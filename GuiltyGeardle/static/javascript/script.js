const input = document.getElementById("guessInput");
const suggestions = document.getElementById("suggestions");
const guessTable = document.querySelector("#guessTable tbody");

let selectedIndex = -1;
let currentSuggestions = [];
let guessCount = 0;
let selectedCharacter = null;
let guessedCharacters = new Set();

function submitSuggestion(character) {
    selectedCharacter = character;

    input.value = character.name;

    suggestions.style.display = "none";
    suggestions.innerHTML = "";

    document.querySelector(".guess-form").requestSubmit();
}

function flipRowCells(row) {
    row.style.visibility = "visible";

    const cells = row.querySelectorAll(".flip-cell");

    cells.forEach((cell, index) => {
        setTimeout(() => {
            cell.classList.add("revealed");
        }, index * 275);
    });
}

input.addEventListener("input", async () => {
    selectedCharacter = null;

    const text = input.value.trim();

    selectedIndex = -1;

    if (text.length === 0) {
        suggestions.style.display = "none";
        suggestions.innerHTML = "";
        currentSuggestions = [];
        return;
    }

    try {
        const response = await fetch(`/search_characters?q=${encodeURIComponent(text)}`);
        const characters = await response.json();

        currentSuggestions = characters.filter(
            character => !guessedCharacters.has(character.name)
        );
        suggestions.innerHTML = "";

        if (currentSuggestions.length === 0) {
            suggestions.style.display = "none";
            return;
        }

        currentSuggestions.forEach((character, index) => {

            const item = document.createElement("div");
            item.className = "suggestion-item";

            item.innerHTML = `
                <img
                    class="suggestion-image"
                    src="/static/images/characters/${character.image}"
                    alt="${character.name}"
                >

                <div class="suggestion-text">
                    <div class="suggestion-name">
                        ${character.name}
                    </div>

                    ${
                        character.alias && character.alias.trim() !== ""
                            ? `<div class="suggestion-alias">Alias: ${character.alias}</div>`
                            : ""
                    }
                </div>
            `;

            item.addEventListener("click", () => {
                submitSuggestion(character);
            });

            suggestions.appendChild(item);

        });

        suggestions.style.display = "block";

    } catch (error) {
        console.error(error);
    }
});

input.addEventListener("keydown", (e) => {

    const items = document.querySelectorAll(".suggestion-item");

    switch (e.key) {

        case "ArrowDown":
            if (items.length === 0) return;
            e.preventDefault();

            selectedIndex++;
            if (selectedIndex >= items.length)
                selectedIndex = 0;

            updateSelection(items);
            break;

        case "ArrowUp":
            if (items.length === 0) return;
            e.preventDefault();

            selectedIndex--;
            if (selectedIndex < 0)
                selectedIndex = items.length - 1;

            updateSelection(items);
            break;

        case "Enter":
            if (items.length === 0) return;
            e.preventDefault();

            const indexToUse = selectedIndex >= 0 ? selectedIndex : 0;
            const character = currentSuggestions[indexToUse];

            if (!character) return;

            submitSuggestion(character);
            break;

        case "Escape":
            suggestions.style.display = "none";
            break;
    }

});

function updateSelection(items) {

    items.forEach(item => {
        item.classList.remove("selected");
    });

    if (selectedIndex >= 0) {
        items[selectedIndex].classList.add("selected");
        items[selectedIndex].scrollIntoView({
            block: "nearest"
        });
    }

}

document.addEventListener("click", (e) => {

    if (!e.target.closest(".input-wrapper") && !e.target.closest(".guess-form")) {
        suggestions.style.display = "none";
    }

});

document.querySelector(".guess-form")
.addEventListener("submit", async (e)=>{

    e.preventDefault();

    if (!selectedCharacter) {
        return;
    }

    const guess = selectedCharacter.name;

    if (guessedCharacters.has(guess)) {
        input.value = "";
        selectedCharacter = null;
        return;
    }

    suggestions.style.display = "none";
    suggestions.innerHTML = "";

    try {
        const response = await fetch("/guess",{
            method:"POST",
            headers:{
                "Content-Type":"application/json"
            },
            body:JSON.stringify({
                guess
            })
        });

        if (!response.ok) {
            const error = await response.json();
            alert(error.error || "Failed to make guess");
            return;
        }

        const result = await response.json();

        guessedCharacters.add(guess);

        if (result.error) {
            alert(result.error);
            return;
        }

        const row = addGuessRow(result);
        flipRowCells(row);

        guessCount++;
        input.value = "";
        selectedCharacter = null;

        if (result.correct) {
            setTimeout(() => {
                input.disabled = true;
                document.querySelector(".guess-button").disabled = true;

                document.getElementById("targetCharacterImage").src =
                    `/static/images/characters/${result.targetImage}`;

                document.getElementById("targetCharacterImage").alt =
                    result.targetName;

                document.getElementById("triesText").textContent =
                    `You got it in ${guessCount} ${guessCount === 1 ? "try" : "tries"}!`;

                const winMessage = document.getElementById("winMessage");
                winMessage.style.display = "block";

                setTimeout(() => {
                    winMessage.scrollIntoView({ behavior: "smooth", block: "center" });
                }, 100);
            }, 500);
        }

        setTimeout(() => {
            row.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 100);
        
        if (guessCount === 1) {
            const accordionButton = document.querySelector(".indicator-accordion .accordion-button");
            if (accordionButton && accordionButton.classList.contains("collapsed")) {
                accordionButton.click();
            }
        }
    } catch (error) {
        console.error("Error:", error);
        alert("An error occurred. Please try again.");
    }
});

function makeCell(status, text){

    let icon = "";

    if (status === "higher") {
        icon = `
        <svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"> <path d="M12 19V5"/> <polyline points="6 11 12 5 18 11"/></svg>
        `;
    }

    if (status === "lower") {
        icon = `
        <svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"> <path d="M12 5v14"/> <polyline points="6 13 12 19 18 13"/></svg>
        `;
;
    }

    return `
    <td class="${status} flip-cell">
        <div class="cell-stack">
            <div class="cell-text">${text}</div>
            ${icon}
        </div>
    </td>`;
}

function addGuessRow(data){
    const row = document.createElement("tr");
    row.style.visibility = "hidden";

    row.innerHTML = `
        <td class="image-cell">
            <img src="/static/images/characters/${data.image}">
        </td>
        ${makeCell(data.correct ? "correct" : "incorrect", data.name)}
        ${makeCell(data.genderStatus, data.genderDisplay)}
        ${makeCell(data.hairStatus, data.hairDisplay)}
        ${makeCell(data.age, data.ageDisplay)}
        ${makeCell(data.heightStatus, data.heightDisplay)}
        ${makeCell(data.gameStatus, data.gameDisplay)}
        ${makeCell(data.archetypeStatus, data.archetypeDisplay)}
        ${makeCell(data.affiliationStatus, data.affiliationDisplay)}
    `;

    document.getElementById("guessTableHead").style.display = "";
    guessTable.prepend(row);

    return row;
}

function updateTimeUntilNext() {
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(0, 0, 0, 0);
    
    const diff = tomorrow - now;
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
    
    document.getElementById("timeUntilNext").textContent =
        `${hours}h ${minutes}m ${seconds}s`;
}

updateTimeUntilNext();
setInterval(updateTimeUntilNext, 1000);