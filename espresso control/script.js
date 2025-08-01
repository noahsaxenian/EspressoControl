console.log("we've reached the script");


function updateStatus(state) {
    const tempDisplay = document.getElementById("currentTemp");
    const setpointDisplay = document.getElementById("setpointTemp");
    const modeSwitch = document.getElementById("modeSwitch");
    const powerSwitch = document.getElementById("powerSwitch");
    const pwmDisplay = document.getElementById("pwmVal");
    const alarmDisplay = document.getElementById("currentAlarm");
    
    pwmDisplay.textContent = state.pwm_val.toFixed(2);
        
    if (state.current_temp === null) {
        tempDisplay.textContent = "--"; // Or another placeholder value
    } else {
        tempDisplay.textContent = state.current_temp.toFixed(1);
    }
    
    if (state.setpoint === null) {
        setpointDisplay.textContent = "--"; // Or another placeholder value
    } else {
        setpointDisplay.textContent = state.setpoint.toFixed(1);
    }
    
    if (document.activeElement !== modeSwitch) {
        modeSwitch.checked = (state.mode === "steam");
    }
    if (document.activeElement !== powerSwitch) {
        powerSwitch.checked = state.power;
    }
    
    updateSwitchAvailability();
    
    if (state.on_interval === true) {
        updateChart(state.current_temp, state.setpoint);
    }
    
    if (state.alarm_time === null) {
        alarmDisplay.textContent = "--";
    } else {
        alarmDisplay.textContent = state.alarm_time;
    }
    
}

function updateSettings(state) {
    const pVal = document.getElementById("pValue");
    const iVal = document.getElementById("iValue");
    const dVal = document.getElementById("dValue");
    const espressoTemp = document.getElementById("espressoTemp");
    const steamTemp = document.getElementById("steamTemp");
    
    pVal.value = state.PID.P;
    iVal.value = state.PID.I;
    dVal.value = state.PID.D;
    espressoTemp.value = state.mode_temps.espresso;
    steamTemp.value = state.mode_temps.steam;

}

function getStatus() {
    sendRequest("/status", {"interval": true});
}

const powerSwitch = document.getElementById('powerSwitch');
const modeSwitch = document.getElementById('modeSwitch');
const modeSlider = document.querySelector('.slider.mode');

// Handle power switch
powerSwitch.addEventListener("change", async (event) => {
    const powerState = event.target.checked ? "on" : "off"; // Determine the state
    await sendRequest("/power", {"power": powerState});
    getStatus();
    updateSwitchAvailability();
});

function updateSwitchAvailability(){
    if (powerSwitch.checked) {
        // Enable the mode switch when power is on
        modeSwitch.disabled = false;
    } else {
        // Disable the mode switch when power is off
        modeSwitch.disabled = true;
    }
}


// Handle mode switch
document.getElementById("modeSwitch").addEventListener("change", async (event) => {
    const mode = event.target.checked ? "steam" : "espresso";
    await sendRequest("/mode", {"mode": mode});
    getStatus();
});


// Function to send HTTP requests
async function sendRequest(endpoint, data) {
    try {
        console.log("sending request", endpoint, data)
        const response = await fetch(endpoint, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(data),
        });
        const result = await response.json();
        console.log(result);
        if (endpoint === "/status") {
            updateStatus(result);
        }
        if (endpoint === "/settings") {
            updateSettings(result);
        }
        if (endpoint === "/history") {
            createHistory(result);
        }

    } catch (error) {
        console.error("Error sending request:", endpoint, error);
    }
}

// Alarm setup
const alarmInput = document.getElementById("alarmTime");
const setAlarmBtn = document.getElementById("setAlarmBtn");

setAlarmBtn.addEventListener("click", async () => {
    const alarmTime = alarmInput.value;

    if (!alarmTime) {
        alert("Please select a time for the alarm.");
        return;
    }
    const now = new Date();
    const timeStr = `${now.getFullYear()}:${now.getMonth() + 1}:${now.getDate()}:${now.getHours()}:${now.getMinutes()}:${now.getSeconds()}`;

    // Send the time to the backend
    await sendRequest("/schedule_alarm", { 
        current_time: timeStr,
        alarm_time: alarmTime
    });
    
    document.getElementById("currentAlarm").textContent = alarmTime;
});

document.getElementById("cancelAlarmBtn").addEventListener("click", async () => {
    await sendRequest("/schedule_alarm", { 
        current_time: null,
        alarm_time: null
    });
    
    document.getElementById("currentAlarm").textContent = "--";
});

const modal = document.getElementById("settingsModal");
const settingsBtn = document.getElementById("settingsBtn");
const closeBtn = document.querySelector(".close");
const saveBtn = document.getElementById("saveSettings");

// Open modal
settingsBtn.onclick = function() {
    modal.style.display = "block";
}

closeBtn.onclick = function() {
    modal.style.display = "none";
}

// Close when clicking outside
window.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}

// Save settings
saveBtn.addEventListener("click", async () => {
    const settings = {
        mode_temps: {
            espresso: parseFloat(document.getElementById("espressoTemp").value),
            steam: parseFloat(document.getElementById("steamTemp").value)
        },
        PID: {
            P: parseFloat(document.getElementById("pValue").value),
            I: parseFloat(document.getElementById("iValue").value),
            D: parseFloat(document.getElementById("dValue").value)
        }
    };
    
    try {
        await sendRequest("/save_settings", settings);
        modal.style.display = "none";
    } catch (error) {
        console.error("Error saving settings:", error);
    }
});

function createHistory(history){
    const tempHistory = history.temp_history;
    const setpointHistory = history.setpoint_history;
    const timeLabels = Array.from({ length: setpointHistory.length }, (_, i) => {
        const step = 10 / (setpointHistory.length - 1); // Calculate the step size
        return -10 + i * step; // Generate each time label
    });
    
    temperatureGraph.data.labels = timeLabels;   
    temperatureGraph.data.datasets[0].data = tempHistory;
    temperatureGraph.data.datasets[1].data = setpointHistory;
    //temperatureGraph.config.options.scales.x.ticks.stepSize = 1;
    
    temperatureGraph.update();
}

let ctx = document.getElementById("temperatureGraph").getContext('2d');

const data = {
    labels: [],  // X-axis labels (could be time or index)
    datasets: [
        { label: "Temp", data: [], borderColor: 'rgba(255, 99, 132, 1)', fill: false, tension: 0.1 },
        { label: "Setpoint", data: [], borderColor: 'rgba(54, 162, 235, 1)', fill: false, tension: 0.1 }
    ]
};

const config = {
    type: 'line',
    data,
    options: {
        responsive: true,
        scales: {
            x: {title: { display: true, text: 'Time (min)' },
                type: "linear"
                },
            y: { title: { display: true, text: 'Temp (°C)' } }
        },
        animation: {
            duration: 0
        }
    }
};

let temperatureGraph = new Chart(ctx, config);

function updateChart(newTemp, newSetpoint) {    
    temperatureGraph.data.datasets[0].data.shift();
    temperatureGraph.data.datasets[1].data.shift();
    
    temperatureGraph.data.datasets[0].data.push(newTemp);
    temperatureGraph.data.datasets[1].data.push(newSetpoint);
    temperatureGraph.update();
}

getStatus();
sendRequest("/history");
sendRequest("/settings");


setInterval(getStatus, 1000);
