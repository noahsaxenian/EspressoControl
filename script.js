console.log("we've reached the script");

function updateState(state) {
    const tempDisplay = document.getElementById("currentTemp");
    const setpointDisplay = document.getElementById("setpointTemp");
    const pVal = document.getElementById("pValue");
    const iVal = document.getElementById("iValue");
    const dVal = document.getElementById("dValue");
    const espressoTemp = document.getElementById("espressoTemp");
    const steamTemp = document.getElementById("steamTemp");
    const modeSwitch = document.getElementById("modeSwitch");
    
    tempDisplay.textContent = state.current_temp.toFixed(1);
    setpointDisplay.textContent = state.setpoint.toFixed(1);
    pVal.value = state.PID.P;
    iVal.value = state.PID.I;
    dVal.value = state.PID.D;
    espressoTemp.value = state.mode_temps.espresso;
    steamTemp.value = state.mode_temps.steam;
    modeSwitch.checked = (state.mode === "steam");

}

// Handle power switch
document.getElementById("powerSwitch").addEventListener("change", async (event) => {
    const powerState = event.target.checked ? "on" : "off"; // Determine the state
    console.log(powerState);
    await sendRequest(`/power/${powerState}`);
});

// Handle mode switch
document.getElementById("modeSwitch").addEventListener("change", async (event) => {
    const mode = event.target.checked ? "steam" : "espresso";
    await sendRequest(`/mode/${mode}`);
});


// Function to send HTTP requests
async function sendRequest(endpoint, data) {
    try {
        const response = await fetch(endpoint, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(data),
        });
        const result = await response.json();
        console.log(result);
    } catch (error) {
        console.error("Error sending request:", error);
    }
}

async function getStatus() {
    try {
        const response = await fetch("/status", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            }
        });
        const result = await response.json();
        console.log(result);
        updateState(result)
    } catch (error) {
        console.error("Error sending request:", error);
    }
}

const modal = document.getElementById("settingsModal");
const settingsBtn = document.getElementById("settingsBtn");
const closeBtn = document.querySelector(".close");
const saveBtn = document.getElementById("saveSettings");

// Open modal
settingsBtn.onclick = function() {
    stopStatusUpdates();
    modal.style.display = "block";
}

// Close modal
function closeModal() {
    modal.style.display = "none";
    startStatusUpdates();
}

closeBtn.onclick = closeModal;

// Close when clicking outside
window.onclick = function(event) {
    if (event.target == modal) {
        closeModal();
    }
}

// Save settings
saveBtn.addEventListener("click", async () => {
    const settings = {
        mode_temps: {
            espresso: parseFloat(document.getElementById("espressoTemp").value),
            steam: parseFloat(document.getElementById("steamTemp").value)
        },
        pid: {
            P: parseFloat(document.getElementById("pValue").value),
            I: parseFloat(document.getElementById("iValue").value),
            D: parseFloat(document.getElementById("dValue").value)
        }
    };
    
    try {
        await sendRequest("/settings", settings);
        closeModal();
    } catch (error) {
        console.error("Error saving settings:", error);
    }
});


let statusInterval; // Store the interval ID

// Function to start the status updates
function startStatusUpdates() {
    console.log("trying to restart status updates");
    statusInterval = setInterval(getStatus, 1000);
}

// Function to stop the status updates
function stopStatusUpdates() {
    if (statusInterval) {
        clearInterval(statusInterval);
        statusInterval = null;
    }
}
// Start the updates when the page loads
startStatusUpdates();
