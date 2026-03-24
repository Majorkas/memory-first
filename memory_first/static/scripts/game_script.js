document.addEventListener("DOMContentLoaded", () => {
  //Wait until Dom is ready so all elements are available to prevent errors
  const root = document.getElementById("memory-game");
  if (!root) {
    //Makes sure the root container is available as game cannot run without
    console.error("[ERROR] memory-game element not found");
    return;
  }
  //Gather all data from API endpoints
  const questionUrl = root.dataset.questionUrl;
  const submitUrl = root.dataset.submitUrl;
  const dashboardUrl = root.dataset.dashboardUrl;
  const csrfToken = root.dataset.csrfToken;
  const totalQuestions = parseInt(root.dataset.totalQuestions, 10);


  //Get all required elements
  const imageEl = document.getElementById("ff-image");
  const questionEl = document.getElementById("q-text");
  const answerEl = document.getElementById("answer");
  const submitBtn = document.getElementById("submit-btn");
  const progressEl = document.getElementById("progress");
  const resultEl = document.getElementById("result");
  const answerLabelEl = document.getElementById("answer-label");

  //Keeps track of how many questions have been answered
  let current = 0;

  async function loadQuestion() {
    //Function to Load the game question


    if (current >= totalQuestions) {
      //Runs game over function once total questions has been reached

      showGameOver();
      return;
    }
    //requests one new question from the backend
    const res = await fetch(questionUrl);
    const data = await res.json();
    //if that fails shows reason to the user
    if (!res.ok) {
      questionEl.textContent = data.detail || "Unable to load question.";
      return;
    }
    //Renders question
    imageEl.src = data.person.image || "";
    questionEl.textContent = data.question;
    answerEl.value = "";
    resultEl.textContent = "";
    progressEl.textContent = `Question ${current + 1} of ${totalQuestions}`;
    answerEl.focus();
  }

  async function submitAnswer() {
    //ignore empty submissions
    if (!answerEl.value.trim()) return;
    //disables submit button to prevent multiple submits
    submitBtn.disabled = true;
    //send answer to backend
    const res = await fetch(submitUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({ answer: answerEl.value }),
    });

    const data = await res.json();
    submitBtn.disabled = false;

    if (!res.ok) {
      resultEl.textContent = data.detail || "Submit failed.";
      return;
    }
    //display if answer was correct and immediately queue next question
    resultEl.textContent = data.correct
      ? "Correct ✅"
      : `Not quite. The answer was: ${data.expected}`;

    current++;
    setTimeout(() => loadQuestion(), 1500);
  }

  function showGameOver() {
    //Game Over Function

    //hide button display the amount of questions complete and redirect back to dashboard after 5 seconds
    imageEl.src = "";
    imageEl.style.display = 'none';
    questionEl.textContent = "Game over! Well done.";
    answerEl.style.display = "none";
    answerLabelEl.style.display = "none";
    submitBtn.style.display = "none";
    progressEl.textContent = `Completed ${totalQuestions} questions`;
    resultEl.textContent = "Redirecting to dashboard in 5 seconds...";



    setTimeout(() => {

      window.location.href = dashboardUrl;
    }, 5000);
  }
  //allows for the use of the enter key to submit an answer
  submitBtn.addEventListener("click", submitAnswer);
  answerEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") submitAnswer();
  });
  //loads question when page is ready
  loadQuestion();
});
