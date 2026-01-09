async function fetchAllWorkouts() {
    try {
        // Pošljemo zahtevo na "/getAllExercises"
        const response = await fetch('http://127.0.0.1:5000/getAllExercises');
        const data = await response.json();
        console.log('Fetched data:', data); // Izpiše celoten JSON odgovor

        const sortedData = sortAlphabetically(data.map(exercise => exercise.name)); // Razvrsti imena vaj
        const dropdown = document.getElementById("workouts");

        // Preverimo, če so že bili podatki naloženi
        if (dropdown.childElementCount === 0) {  // Če ni nobenih možnosti (samo privzeta)

            // Dodaj vse unikatne vaje v dropdown
            sortedData.forEach(name => {
                const option = document.createElement("option");
                option.value = name;
                option.textContent = name;
                dropdown.appendChild(option);
                console.log(option);
            });
        }

        // Prikažemo podatke v elementu z ID-jem "test"
        const testElement = document.getElementById("test");
        testElement.innerText = JSON.stringify(data, null, 2);

    } catch (error) {
        console.error("Napaka pri pridobivanju podatkov:", error);
    }
}

function sortAlphabetically(array) {
    return array.sort((a, b) => a.localeCompare(b, 'sl')); // Upoštevaj slovensko abecedo
}

let selectedExercise = "";

// Funkcija za posodobitev trenutne izbire v dropdownu
document.getElementById("workouts").addEventListener('change', function() {
    selectedExercise = this.value;  // Shranimo izbrano vrednost
    console.log("Trenutno izbrana vadba:", selectedExercise);
});