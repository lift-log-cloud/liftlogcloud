//TODO add unit tests

const paneContainer = document.getElementById('pane-container');
var weightCol = null;
var repCol = null;
document.addEventListener("DOMContentLoaded", () =>
{
  initializeStorage();

  const paneContainer = document.getElementById("pane-container");
  const buttons = document.querySelectorAll("nav button");

  buttons.forEach(button =>
  {
    button.addEventListener("click", () =>
    {
      const pane = button.dataset.pane;

      fetch(`${pane}.html`)
        .then(response => response.text())
        .then(data =>
        {
          paneContainer.innerHTML = data;

          switch (pane)
          {
            case "calendar":
              break;
            case "workout":
              reloadExerciseDropdown();
              weightCol = document.getElementById("weightCol");
              repCol = document.getElementById("repCol");
              break;
            case "stats":
              break;
          }

        })
        .catch(err => console.error("Error loading pane:", err));
    });
  });

  // Load default pane
  fetch("calendar.html")
    .then(response => response.text())
    .then(data => paneContainer.innerHTML = data)
    .catch(err => console.error("Error loading default pane:", err));
});


// Load default pane
fetch("calendar.html")
  .then(response => response.text())
  .then(data => paneContainer.innerHTML = data);



// auto call function with name of buttons id 
paneContainer.addEventListener("click", (event) =>
{
  if (event.target && event.target.classList.length > 0)
  {
    event.target.classList.forEach((className) =>
    {
      const functionName = className.replace(/-/g, "_");
      if (typeof window[functionName] === "function")
      {
        window[functionName]();
      }
    });
  }
});


function selectedButton(buttonNumber)
{
  if (buttonNumber == 1)
  {
    document.getElementById("home_button").style.background = "linear-gradient(145deg, #A677FF, #33166A)"
    document.getElementById("workout_button").style.background = "none"
    document.getElementById("chart_button").style.background = "none"
  } else if (buttonNumber == 2)
  {
    document.getElementById("home_button").style.background = "none"
    document.getElementById("workout_button").style.background = "linear-gradient(145deg, #A677FF, #33166A)"
    document.getElementById("chart_button").style.background = "none"
  } else
  {
    document.getElementById("home_button").style.background = "none"
    document.getElementById("workout_button").style.background = "none"
    document.getElementById("chart_button").style.background = "linear-gradient(145deg, #A677FF, #33166A)"
  }
}


// kaj je to???? sploh ne dela k se page dimanocno loada. bruh
// 
// const sets = document.getElementById('sets');

// sets.addEventListener('input', (event) =>
// {
//   const value = parseInt(sets.value, 10);
//   if (value < parseInt(sets.min, 10))
//   {
//     sets.value = sets.min; // Ensures the value doesn't go below the minimum
//   }
// });


// const reps = document.getElementById('reps');

// reps.addEventListener('input', (event) =>
// {
//   const value = parseInt(reps.value, 10);
//   if (value < parseInt(reps.min, 10))
//   {
//     reps.value = reps.min; // Ensures the value doesn't go below the minimum
//   }
// });

// const weight = document.getElementById('weight');

// weight.addEventListener('input', (event) =>
// {
//   const value = parseInt(weight.value, 10);
//   if (value < parseInt(weight.min, 10))
//   {
//     weight.value = weight.min; // Ensures the value doesn't go below the minimum
//   }
// });
//
//

function btn_add()
{
  const date = new Date().toISOString().slice(0, 10);
  const workout = document.getElementById("exercise").value;
  const sets = parseInt(document.getElementById("sets").value, 10);
  const reps = [];
  const weight = [];
  for (var i = 0; i < sets; i++)
  {
    reps.push(parseInt(document.getElementById(`reps${i}`).value, 10));
    weight.push(parseInt(document.getElementById(`weight${i}`).value, 10));
  }
  saveTrainingSession(date, workout, sets, reps, weight);
}
function btn_add_workout()
{
  // !ta funkcija naj odpre popup al karkoli
  //TODO remove
  //EXAMPLE 
  var workoutname = "skullcrushers"; // read from a field
  addWorkoutToSelection(workoutname);
  //EXAMPLE END

  // v novem popupu naj bo button ok/add/karkoli ki poklice tudi to funkcijo (poleg addWorkoutToSelection).
  reloadExerciseDropdown();
}

function reloadExerciseDropdown()
{
  const exerciseSelect = document.getElementById("exercise");
  if (exerciseSelect)
  {
    exerciseSelect.innerHTML = "";
    const workoutSel = loadWorkoutSelection();
    workoutSel.forEach(workoutName =>
    {
      const option = document.createElement("option");
      option.value = workoutName;
      option.textContent = workoutName;
      option.className = "exercise-item";
      exerciseSelect.appendChild(option);
    });
  } else
  {
    console.error("Cannot find element with id 'exercise'");
  }
}

// gre za to ->   <select id="exercise">
function addWorkoutToSelection(workoutName)
{
  const data = JSON.parse(localStorage.getItem('fitnessData')) || { WorkoutSelection: [], sessions: [] };
  if (!data.WorkoutSelection.includes(workoutName))
  {
    data.WorkoutSelection.push(workoutName);
    localStorage.setItem('fitnessData', JSON.stringify(data));
  }
}

function loadWorkoutSelection()
{
  const data = JSON.parse(localStorage.getItem('fitnessData')) || { WorkoutSelection: [], sessions: [] };
  return data.WorkoutSelection || [];
}

// return all training sessions on that date
// loadTrainingSessionByDate('2024-06-01')
function loadTrainingSessionByDate(date)
{
  sessions = loadTrainingSessions();
  return sessions.filter(session => session.date === date);
}

// data -> string date, vaja string, sets int, reps int, weight int
function saveTrainingSession(date, workout, sets, reps, weight)
{
  const data = JSON.parse(localStorage.getItem('fitnessData')) || { WorkoutSelection: [], sessions: [] };
  data.sessions.push({
    date,
    workout,
    sets,
    reps,
    weight
  });
  localStorage.setItem('fitnessData', JSON.stringify(data));
}

// return a list of all trainign sessions
function loadTrainingSessions()
{
  const data = JSON.parse(localStorage.getItem('fitnessData')) || { WorkoutSelection: [], sessions: [] };
  return data.sessions;
}

function initializeStorage()
{
  if (!localStorage.getItem('fitnessData'))
  {
    const defaultData = {
      WorkoutSelection: ["bench", "squat", "deadlift"],
      sessions: []
    };
    localStorage.setItem('fitnessData', JSON.stringify(defaultData));
  }
}

function clearLocalStorage() 
{
  localStorage.removeItem('fitnessData');
}

function setKgRepsBySets(sets)
{
  // Get current child count
  var childCount = weightCol.childElementCount;

  // If the number of sets matches, do nothing
  if (sets == childCount) return;

  // Remove excess elements if sets are reduced
  if (sets < childCount)
  {
    for (var i = childCount; i > sets; i--)
    {
      weightCol.removeChild(weightCol.lastElementChild);
      repCol.removeChild(repCol.lastElementChild);
    }
  }

  // Add new elements if sets are increased
  for (var i = childCount; i < sets; i++)
  {
    var idReps = "reps" + i;
    var idWeight = "weight" + i;

    var repsWrapper = document.createElement("div");
    repsWrapper.className = "input_wrapper";
    repsWrapper.innerHTML = `
      <button class="btn-decrement" onclick="document.getElementById('${idReps}').value = Math.max(1, parseInt(document.getElementById('${idReps}').value) - 1)">−</button>
      <input id="${idReps}" type="number" value="1" min="1">
      <button class="btn-increment" onclick="document.getElementById('${idReps}').value = parseInt(document.getElementById('${idReps}').value) + 1">+</button>
    `;

    var weightWrapper = document.createElement("div");
    weightWrapper.className = "input_wrapper";
    weightWrapper.innerHTML = `
      <button class="btn-decrement" onclick="document.getElementById('${idWeight}').value = Math.max(0, parseInt(document.getElementById('${idWeight}').value) - 1)">−</button>
      <input id="${idWeight}" type="number" value="0" min="0">
      <button class="btn-increment" onclick="document.getElementById('${idWeight}').value = parseInt(document.getElementById('${idWeight}').value) + 1">+</button>
    `;
    repCol.appendChild(repsWrapper);
    weightCol.appendChild(weightWrapper);
  }
}

