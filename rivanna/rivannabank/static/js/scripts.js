
document.addEventListener("DOMContentLoaded", () => {
    if (window.location.href.includes("Check-Balance")) {
        initCheckBalanceForm();
    }
    const menuBtn = document.querySelector(".menu-btn");
    const menuOptions = document.querySelector(".menu-options");

    menuBtn.addEventListener("click", () => {
        menuOptions.classList.toggle("show-menu-options");
    });
    // Toggle password visibility
    window.togglePassword = function(fieldId, button) {
        const field = document.getElementById(fieldId);
        if (field.type === "password") {
            field.type = "text";
            button.textContent = "🙈"; // hide icon
        } else {
            field.type = "password";
            button.textContent = "👁️"; // show icon
        }
    };
});

function initCheckBalanceForm() {
    const form = document.querySelector("form");
    const requestDiv = document.querySelector(".request");
    const responseSection = document.querySelector(".response");
    const responseDiv = document.querySelector(".response .sub-heading");

    const spinner = document.createElement("p");
    spinner.textContent = "⏳ Fetching balance...";
    spinner.style.fontWeight = "bold";

    form.addEventListener("submit", function (e) {
        e.preventDefault();

        // Clear any previous result and show spinner
        responseDiv.innerHTML = "";
        responseDiv.appendChild(spinner);

        // Hide the form section and show response block
        requestDiv.style.display = "none";
        responseSection.style.display = "block";

        const formData = new FormData(form);

        fetch("/Check-Balance", {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": formData.get("csrfmiddlewaretoken"),
            },
            body: formData,
        })
        .then((res) => res.json())
        .then((data) => {
            responseDiv.innerHTML = ""; // Remove spinner

            if (data.balance !== undefined) {
                responseDiv.innerHTML = `
                    <p>Your current balance is</p>
                    <p class="amount">$${parseFloat(data.balance).toFixed(2)}</p>
                    <div class="form-buttons">
                        
                        <a href="Check-Balance" class="btn signup">Back</a>
                        <a href="/" class="btn signup">Go to home</a>
                    </div>
                `;
            } else {
                responseDiv.innerHTML = `<p style="color: red;">${data.error}</p>`;
                // Optionally show form again if there's an error
                requestDiv.style.display = "block";
                responseSection.style.display = "none";
            }
        })
        .catch((err) => {
            console.error(err);
            responseDiv.innerHTML = `<p style="color: red;">Something went wrong. Try again.</p>`;
            requestDiv.style.display = "block";
            responseSection.style.display = "none";
        });
    });
}