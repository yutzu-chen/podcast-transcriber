/**
 * Podcast Transcriber Web App - Frontend JavaScript
 */

class PodcastTranscriber {
  constructor() {
    this.sessionId = null;
    this.isRecording = false;
    this.transcriptions = [];
    this.currentSentence = "";
    this.pollInterval = null;

    this.initializeElements();
    this.bindEvents();
    this.generateSessionId();
  }

  initializeElements() {
    this.playButton = document.getElementById("playButton");
    this.playIcon = this.playButton.querySelector(".play-icon");
    this.transcriptionText = document.getElementById("transcriptionText");
    this.dictionaryContent = document.getElementById("dictionaryContent");
    this.loadingOverlay = document.getElementById("loadingOverlay");
  }

  bindEvents() {
    this.playButton.addEventListener("click", () => this.toggleRecording());

    // Bind word click events (delegated)
    this.transcriptionText.addEventListener("click", (e) => {
      if (e.target.classList.contains("word")) {
        this.lookupWord(e.target.textContent);
      }
    });
  }

  generateSessionId() {
    this.sessionId = `session_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
  }

  async toggleRecording() {
    if (this.isRecording) {
      await this.stopRecording();
    } else {
      await this.startRecording();
    }
  }

  async startRecording() {
    try {
      this.showLoading("Starting recording...");

      const response = await fetch("/api/start-recording", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: this.sessionId,
        }),
      });

      const result = await response.json();

      if (result.success) {
        this.isRecording = true;
        this.updateUI();
        this.startPolling();
        this.hideLoading();
      } else {
        throw new Error(result.error || "Failed to start recording");
      }
    } catch (error) {
      console.error("Error starting recording:", error);
      this.hideLoading();
      alert("Failed to start recording: " + error.message);
    }
  }

  async stopRecording() {
    try {
      this.showLoading("Stopping recording...");

      const response = await fetch("/api/stop-recording", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: this.sessionId,
        }),
      });

      const result = await response.json();

      if (result.success) {
        this.isRecording = false;
        this.stopPolling();
        this.updateUI();
        this.hideLoading();
      } else {
        throw new Error(result.error || "Failed to stop recording");
      }
    } catch (error) {
      console.error("Error stopping recording:", error);
      this.hideLoading();
      alert("Failed to stop recording: " + error.message);
    }
  }

  startPolling() {
    this.pollInterval = setInterval(() => {
      this.pollTranscriptions();
    }, 1000); // Poll every second
  }

  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  async pollTranscriptions() {
    try {
      const response = await fetch(`/api/transcriptions/${this.sessionId}`);
      const result = await response.json();

      if (result.success) {
        this.updateTranscriptions(
          result.transcriptions,
          result.current_sentence
        );
      }
    } catch (error) {
      console.error("Error polling transcriptions:", error);
    }
  }

  updateTranscriptions(transcriptions, currentSentence) {
    // Update transcriptions if they've changed
    if (
      JSON.stringify(transcriptions) !== JSON.stringify(this.transcriptions)
    ) {
      this.transcriptions = transcriptions;
      this.renderTranscriptions();
    }

    // Update current sentence if it's changed
    if (currentSentence !== this.currentSentence) {
      this.currentSentence = currentSentence;
      this.renderCurrentSentence();
    }
  }

  renderTranscriptions() {
    const container = this.transcriptionText;

    // Clear existing content
    container.innerHTML = "";

    // Render completed sentences
    this.transcriptions.forEach((transcription) => {
      const sentenceDiv = document.createElement("div");
      sentenceDiv.className = "sentence completed";
      sentenceDiv.innerHTML = this.formatSentenceWithClickableWords(
        transcription.text
      );
      container.appendChild(sentenceDiv);
    });

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
  }

  renderCurrentSentence() {
    const container = this.transcriptionText;

    // Remove existing current sentence
    const existingCurrent = container.querySelector(".sentence.current");
    if (existingCurrent) {
      existingCurrent.remove();
    }

    // Add new current sentence if it exists
    if (this.currentSentence) {
      const sentenceDiv = document.createElement("div");
      sentenceDiv.className = "sentence current";
      sentenceDiv.innerHTML = this.formatSentenceWithClickableWords(
        this.currentSentence
      );
      container.appendChild(sentenceDiv);

      // Scroll to bottom
      container.scrollTop = container.scrollHeight;
    }
  }

  formatSentenceWithClickableWords(text) {
    // Split text into words and punctuation, making words clickable
    return text.replace(/\b(\w+)\b/g, '<span class="word">$1</span>');
  }

  async lookupWord(word) {
    try {
      this.showLoading("Looking up word...");

      const response = await fetch(
        `/api/dictionary/${encodeURIComponent(word)}`
      );
      const result = await response.json();

      if (result.success) {
        this.displayWordDefinition(word, result.definition);
      } else {
        throw new Error(result.error || "Failed to lookup word");
      }
    } catch (error) {
      console.error("Error looking up word:", error);
      this.displayWordError(word, error.message);
    } finally {
      this.hideLoading();
    }
  }

  displayWordDefinition(word, definition) {
    const container = this.dictionaryContent;

    let html = `
            <div class="word-header">
                <div class="word-title">${word}</div>
                <div class="star-icon">☆</div>
            </div>
        `;

    if (definition.phonetic) {
      html += `<div class="phonetic">${definition.phonetic}</div>`;
    }

    html += '<div class="separator"></div>';

    if (definition.part_of_speech) {
      html += `<div class="part-of-speech">${definition.part_of_speech}</div>`;
    }

    if (definition.definitions && definition.definitions.length > 0) {
      definition.definitions.forEach((def, index) => {
        html += `<div class="definition">• ${def}</div>`;
      });
    }

    if (definition.similar_words) {
      const english = definition.similar_words.english || [];
      const german = definition.similar_words.german || [];

      if (english.length > 0 || german.length > 0) {
        html += '<div class="similar-words">';
        html += '<div class="similar-words-title">SIMILAR WORDS</div>';

        if (english.length > 0) {
          html += `<div class="similar-words-content">Similar words in English: ${english.join(
            ", "
          )}</div>`;
        }

        if (german.length > 0) {
          html += `<div class="similar-words-content">Similar words in Deutsch: ${german.join(
            ", "
          )}</div>`;
        }

        html += "</div>";
      }
    }

    container.innerHTML = html;
  }

  displayWordError(word, error) {
    const container = this.dictionaryContent;
    container.innerHTML = `
            <div class="word-header">
                <div class="word-title">${word}</div>
            </div>
            <div class="phonetic">/${word.toLowerCase()}/</div>
            <div class="separator"></div>
            <div class="part-of-speech">ERROR</div>
            <div class="definition">Failed to load definition: ${error}</div>
        `;
  }

  updateUI() {
    if (this.isRecording) {
      this.playButton.classList.add("recording");
      this.playIcon.textContent = "⏹";
    } else {
      this.playButton.classList.remove("recording");
      this.playIcon.textContent = "▶";
    }
  }

  showLoading(message = "Loading...") {
    this.loadingOverlay.querySelector("p").textContent = message;
    this.loadingOverlay.classList.add("show");
  }

  hideLoading() {
    this.loadingOverlay.classList.remove("show");
  }
}

// Initialize the app when the page loads
document.addEventListener("DOMContentLoaded", () => {
  window.podcastTranscriber = new PodcastTranscriber();
});

// Handle page unload
window.addEventListener("beforeunload", () => {
  if (window.podcastTranscriber && window.podcastTranscriber.isRecording) {
    window.podcastTranscriber.stopRecording();
  }
});
