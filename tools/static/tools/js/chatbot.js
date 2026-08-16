// Chat Bot page behaviour: sends the user's message to the backend,
// shows a bouncing "typing..." indicator while waiting, then replaces
// it with the bot's reply once it arrives (with a small realistic delay
// so it doesn't feel instant / robotic).

(function () {
  const form = document.getElementById('chat-form');
  if (!form) return; // Not on the chat bot page.

  const window_ = document.getElementById('chat-window');
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send');
  const suggestions = document.getElementById('chat-suggestions');
  const askUrl = form.dataset.askUrl;

  function scrollToBottom() {
    window_.scrollTop = window_.scrollHeight;
  }

  function appendMessage(text, sender) {
    const msg = document.createElement('div');
    msg.className = `chat-msg ${sender} pop-in`;

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.textContent = sender === 'user' ? 'YOU' : 'IQ';

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    bubble.textContent = text;

    msg.appendChild(avatar);
    msg.appendChild(bubble);
    window_.appendChild(msg);
    scrollToBottom();
    return msg;
  }

  function showTypingIndicator() {
    const msg = document.createElement('div');
    msg.className = 'chat-msg bot pop-in';
    msg.id = 'chat-typing-msg';

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.textContent = 'IQ';

    const typing = document.createElement('div');
    typing.className = 'chat-bubble chat-typing';
    typing.innerHTML = '<span></span><span></span><span></span>';

    msg.appendChild(avatar);
    msg.appendChild(typing);
    window_.appendChild(msg);
    scrollToBottom();
  }

  function removeTypingIndicator() {
    const el = document.getElementById('chat-typing-msg');
    if (el) el.remove();
  }

  function getCsrfToken() {
    const el = form.querySelector('input[name="csrfmiddlewaretoken"]');
    return el ? el.value : '';
  }

  async function sendMessage(text) {
    appendMessage(text, 'user');
    input.value = '';
    input.disabled = true;
    sendBtn.disabled = true;

    showTypingIndicator();

    // Minimum "thinking" delay so the reply never feels instant, even
    // if the server responds immediately — mimics a real person typing.
    const minDelay = new Promise((resolve) => {
      setTimeout(resolve, 900 + Math.random() * 900);
    });

    try {
      const [response] = await Promise.all([
        fetch(askUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
          },
          body: JSON.stringify({ message: text }),
        }),
        minDelay,
      ]);

      const data = await response.json();
      removeTypingIndicator();
      appendMessage(data.reply || "Sorry, I didn't catch that — could you rephrase?", 'bot');
    } catch (err) {
      removeTypingIndicator();
      appendMessage("Something went wrong reaching the server — please try again.", 'bot');
    } finally {
      input.disabled = false;
      sendBtn.disabled = false;
      input.focus();
    }
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    sendMessage(text);
  });

  if (suggestions) {
    suggestions.querySelectorAll('.chat-suggestion').forEach((btn) => {
      btn.addEventListener('click', () => {
        sendMessage(btn.textContent.trim());
      });
    });
  }
})();
