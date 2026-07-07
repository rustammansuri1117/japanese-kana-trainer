/**
 * quiz.js — the core learning loop. Handles the setup screen (script, quiz
 * type, timer) and the quiz stage itself: fetching a question, collecting
 * an answer (text input or multiple choice), submitting it, showing the
 * hanko-stamp feedback, and auto-advancing to the next question.
 */
let quizConfig = { script: "hiragana", quizType: "char_to_romaji", reviewMistakes: false, timerSeconds: null };
let currentQuestion = null;
let questionStartTime = null;
let timerInterval = null;
let sessionStats = { answered: 0, correct: 0 };

function setupOptionCard(groupSel, value, attr) {
  document.querySelectorAll(groupSel).forEach(card => {
    card.classList.toggle("selected", card.dataset[attr] === value);
  });
}

function initQuizSetup() {
  document.querySelectorAll("[data-script]").forEach(card => {
    card.addEventListener("click", () => {
      quizConfig.script = card.dataset.script;
      setupOptionCard("[data-script]", card.dataset.script, "script");
    });
  });
  document.querySelectorAll("[data-quiztype]").forEach(card => {
    card.addEventListener("click", () => {
      quizConfig.quizType = card.dataset.quiztype;
      quizConfig.reviewMistakes = card.dataset.quiztype === "review_mistakes";
      if (quizConfig.reviewMistakes) quizConfig.quizType = "mixed";
      quizConfig.timerSeconds = card.dataset.quiztype === "timed" ? 10 : null;
      setupOptionCard("[data-quiztype]", card.dataset.quiztype, "quiztype");
      document.getElementById("timer-select-wrap").classList.toggle("hidden", card.dataset.quiztype !== "timed");
    });
  });
  document.getElementById("timer-select").addEventListener("change", (e) => {
    const v = e.target.value;
    quizConfig.timerSeconds = v === "unlimited" ? null : parseInt(v, 10);
  });

  // Pre-select from query params (e.g. quiz.html?script=hiragana)
  const params = new URLSearchParams(location.search);
  if (params.get("script")) {
    quizConfig.script = params.get("script");
    setupOptionCard("[data-script]", quizConfig.script, "script");
  }

  document.getElementById("start-quiz-btn").addEventListener("click", startQuiz);
}

function startQuiz() {
  sessionStats = { answered: 0, correct: 0 };
  document.getElementById("quiz-setup").classList.add("hidden");
  document.getElementById("quiz-stage").classList.remove("hidden");
  loadNextQuestion();
}

async function loadNextQuestion() {
  clearInterval(timerInterval);
  const feedback = document.getElementById("quiz-feedback-overlay");
  if (feedback) feedback.remove();

  const promptCard = document.getElementById("quiz-prompt-card");
  promptCard.innerHTML = `<p class="text-muted">Loading next question…</p>`;
  document.getElementById("quiz-answer-area").innerHTML = "";

  try {
    currentQuestion = await Api.randomQuestion({
      script: quizConfig.script,
      quiz_type: quizConfig.quizType,
      review_mistakes: quizConfig.reviewMistakes,
      timer_seconds: quizConfig.timerSeconds,
    });
  } catch (err) {
    promptCard.innerHTML = `<p class="text-muted">${err.message}</p><a href="quiz.html" class="btn btn-outline mt-16">Back to setup</a>`;
    return;
  }

  renderQuestion();
  updateProgressRow();
  questionStartTime = Date.now();

  if (currentQuestion.timer_seconds) {
    startTimer(currentQuestion.timer_seconds);
  }
}

function renderQuestion() {
  const promptCard = document.getElementById("quiz-prompt-card");
  const isCharPrompt = currentQuestion.quiz_type !== "romaji_to_char" && !/^[a-z]+$/i.test(currentQuestion.prompt) || currentQuestion.prompt.match(/[^\x00-\x7F]/);
  const promptClass = /[^\x00-\x7F]/.test(currentQuestion.prompt) ? "quiz-prompt-char" : "quiz-prompt-romaji";
  promptCard.innerHTML = `<div class="${promptClass}">${currentQuestion.prompt}</div>`;

  const answerArea = document.getElementById("quiz-answer-area");
  if (currentQuestion.options && currentQuestion.options.length) {
    answerArea.innerHTML = `
      <div class="quiz-mc-grid">
        ${currentQuestion.options.map(opt => `<button class="quiz-mc-option" data-answer="${opt}">${opt}</button>`).join("")}
      </div>
    `;
    answerArea.querySelectorAll(".quiz-mc-option").forEach(btn => {
      btn.addEventListener("click", () => submitAnswer(btn.dataset.answer, btn));
    });
  } else {
    answerArea.innerHTML = `
      <input type="text" id="quiz-text-input" class="quiz-answer-input" placeholder="Type the romaji…" autocomplete="off" autocapitalize="off" spellcheck="false">
      <br><button class="btn btn-primary" id="quiz-submit-btn">Submit</button>
    `;
    const input = document.getElementById("quiz-text-input");
    input.focus();
    input.addEventListener("keypress", (e) => { if (e.key === "Enter") submitAnswer(input.value); });
    document.getElementById("quiz-submit-btn").addEventListener("click", () => submitAnswer(input.value));
  }
}

function startTimer(seconds) {
  let remaining = seconds;
  const timerEl = document.getElementById("quiz-timer");
  timerEl.textContent = remaining;
  timerEl.classList.remove("hidden");
  timerInterval = setInterval(() => {
    remaining -= 1;
    timerEl.textContent = remaining;
    if (remaining <= 0) {
      clearInterval(timerInterval);
      submitAnswer(""); // time's up -> counts as incorrect
    }
  }, 1000);
}

async function submitAnswer(answer, clickedBtn = null) {
  clearInterval(timerInterval);
  const responseTime = Date.now() - questionStartTime;
  document.querySelectorAll(".quiz-mc-option, #quiz-submit-btn").forEach(el => el.disabled = true);

  let result;
  try {
    result = await Api.checkAnswer({
      question_id: currentQuestion.question_id,
      quiz_type: currentQuestion.quiz_type,
      script: currentQuestion.script,
      submitted_answer: answer,
      response_time_ms: responseTime,
    });
  } catch (err) {
    showToast(err.message, { icon: "⚠️" });
    return;
  }

  sessionStats.answered++;
  if (result.correct) sessionStats.correct++;

  if (clickedBtn) {
    clickedBtn.classList.add(result.correct ? "correct" : "incorrect");
    if (!result.correct) {
      document.querySelectorAll(".quiz-mc-option").forEach(b => {
        if (b.dataset.answer.toLowerCase() === result.correct_answer.toLowerCase()) b.classList.add("correct");
      });
    }
  }

  showFeedback(result);
  updateProgressRow();

  if (result.leveled_up) {
    Sound.levelUp();
    fireConfetti();
    showToast(`Level up! You're now level ${result.new_level} 🎉`, { icon: "🌟", duration: 4000 });
  }
  result.unlocked_achievements.forEach(title => {
    showToast(`Achievement unlocked: ${title}`, { icon: "🏅", duration: 4000 });
  });

  setTimeout(loadNextQuestion, 1600);
}

function showFeedback(result) {
  result.correct ? Sound.correct() : Sound.wrong();
  const promptCard = document.getElementById("quiz-prompt-card");
  const overlay = document.createElement("div");
  overlay.className = "quiz-feedback-overlay";
  overlay.id = "quiz-feedback-overlay";

  if (result.correct) {
    overlay.innerHTML = `
      <div class="flex-col items-center">
        <div class="hanko-stamp stamp-in">正</div>
        <p class="quiz-result-detail">${result.character} = <strong>${result.correct_answer}</strong> — "${result.example_word}" (${result.meaning})</p>
      </div>
    `;
  } else {
    overlay.innerHTML = `
      <div class="flex-col items-center">
        <div class="hanko-stamp wrong stamp-in">
          <span class="brush-x"><svg viewBox="0 0 100 100"><path d="M20,20 L80,80 M80,20 L20,80"/></svg></span>
        </div>
        <p class="quiz-result-detail">Correct answer: <strong>${result.correct_answer}</strong> — "${result.example_word}" (${result.meaning})</p>
      </div>
    `;
  }
  promptCard.appendChild(overlay);
}

function updateProgressRow() {
  document.getElementById("quiz-session-score").textContent = `${sessionStats.correct} / ${sessionStats.answered} correct`;
  document.getElementById("quiz-mode-label").textContent = `${quizConfig.script} · ${quizConfig.reviewMistakes ? "review mistakes" : quizConfig.quizType.replace(/_/g, " ")}`;
}

function endQuizSession() {
  document.getElementById("quiz-stage").classList.add("hidden");
  document.getElementById("quiz-setup").classList.remove("hidden");
  clearInterval(timerInterval);
}
