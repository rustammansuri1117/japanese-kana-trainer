/**
 * flashcards.js — flip-card study mode with shuffle, prev/next, and
 * keyboard shortcuts (Space = flip, ←/→ = prev/next, S = shuffle).
 */
let deck = [];
let deckIndex = 0;
let isFlipped = false;
let seenCount = 0;

function renderCard() {
  const card = deck[deckIndex];
  if (!card) return;
  document.getElementById("fc-front-char").textContent = card.character;
  document.getElementById("fc-back-romaji").textContent = card.romaji;
  document.getElementById("fc-back-example").textContent = `${card.example_word} — ${card.meaning}`;
  document.getElementById("fc-back-tip").textContent = card.memory_tip;
  document.getElementById("fc-progress-label").textContent = `Card ${deckIndex + 1} of ${deck.length}`;
  document.getElementById("fc-progress-bar").style.width = `${((deckIndex + 1) / deck.length) * 100}%`;

  const flashcardEl = document.getElementById("flashcard");
  flashcardEl.classList.remove("flipped");
  isFlipped = false;
}

function flipCard() {
  const flashcardEl = document.getElementById("flashcard");
  isFlipped = !isFlipped;
  flashcardEl.classList.toggle("flipped", isFlipped);
  if (isFlipped) {
    Sound.click();
    seenCount++;
  }
}

function nextCard() {
  deckIndex = (deckIndex + 1) % deck.length;
  renderCard();
}
function prevCard() {
  deckIndex = (deckIndex - 1 + deck.length) % deck.length;
  renderCard();
}
function shuffleDeck() {
  for (let i = deck.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }
  deckIndex = 0;
  renderCard();
  showToast("Deck shuffled!", { icon: "🔀" });
}

async function logFlashcardSession() {
  if (!Auth.isLoggedIn() || seenCount === 0) return;
  try {
    await Api.logSession({
      session_type: "flashcards",
      script: window.KANA_SCRIPT || "mixed",
      questions_answered: seenCount,
      correct_answers: seenCount,
    });
  } catch (e) { /* non-critical */ }
}

async function initFlashcards(script) {
  const stage = document.getElementById("flashcard-stage");
  try {
    const chars = script === "hiragana" ? await Api.listHiragana()
      : script === "katakana" ? await Api.listKatakana()
      : [...await Api.listHiragana(), ...await Api.listKatakana()];
    deck = chars;
    shuffleArrayInPlace(deck);
    stage.classList.remove("hidden");
    renderCard();
  } catch (err) {
    stage.innerHTML = `<p class="text-muted text-center">Couldn't load flashcards — make sure the backend server is running.</p>`;
  }
}

function shuffleArrayInPlace(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
}

document.addEventListener("keydown", (e) => {
  if (!document.getElementById("flashcard-stage") || document.getElementById("flashcard-stage").classList.contains("hidden")) return;
  if (e.code === "Space") { e.preventDefault(); flipCard(); }
  if (e.code === "ArrowRight") nextCard();
  if (e.code === "ArrowLeft") prevCard();
  if (e.code === "KeyS") shuffleDeck();
});

window.addEventListener("beforeunload", logFlashcardSession);
