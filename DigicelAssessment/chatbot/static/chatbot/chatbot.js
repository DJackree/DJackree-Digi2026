/**
 * Chatbot Phase 3 — JSON chat transport with CSRF, loading state, transcript bubbles.
 */
(function () {
  "use strict";

  var root = document.getElementById("chatAppRoot");
  if (!root) return;

  var transcript = document.getElementById("chatTranscript");
  var viewport = document.getElementById("chatTranscriptViewport");
  var textarea = document.getElementById("chatMessage");
  var sendBtn = document.getElementById("sendBtn");
  var newChatBtn = document.getElementById("newChatBtn");
  var sessionInput = document.getElementById("chatSessionId");
  var ariaStatus = document.getElementById("chatAriaStatus");
  var statusLine = document.getElementById("chatStatusLine");

  var postMessageUrl = root.dataset.postMessageUrl;
  var newSessionUrl = root.dataset.newSessionUrl;
  var chatHomeUrl = root.dataset.chatHomeUrl || "/chatbot/";

  var busy = false;

  function getCsrfToken() {
    var field = document.querySelector("[name='csrfmiddlewaretoken']");
    return field && field.value ? field.value : "";
  }

  async function chatPost(url, payload) {
    var headers = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    var token = getCsrfToken();
    if (token) headers["X-CSRFToken"] = token;

    var res = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: headers,
      body: JSON.stringify(payload),
    });

    var data = {};
    try {
      data = await res.json();
    } catch (e) {}
    return { ok: res.ok, status: res.status, data: data };
  }

  function setBusy(flag) {
    busy = !!flag;
    if (sendBtn) sendBtn.disabled = busy;
    if (textarea) textarea.disabled = busy;
    if (newChatBtn) newChatBtn.disabled = busy;
    var suggests = root.querySelectorAll(".chat-suggestion");
    suggests.forEach(function (b) {
      b.disabled = busy;
    });
  }

  function announce(msg) {
    if (ariaStatus) ariaStatus.textContent = msg || "";
  }

  function removeEmptyState() {
    var es = document.getElementById("chatEmptyState");
    if (es) es.remove();
  }

  function scrollToBottom() {
    if (!viewport) return;
    viewport.scrollTop = viewport.scrollHeight;
  }

  function appendBubble(kind, bodyText) {
    if (!transcript || !bodyText) return;
    removeEmptyState();

    var outer = document.createElement("div");
    outer.className =
      kind === "user"
        ? "d-flex justify-content-end mb-3"
        : kind === "error"
          ? "d-flex justify-content-center mb-3"
          : "d-flex justify-content-start mb-3";

    var bubble = document.createElement("div");
    bubble.style.maxWidth = "85%";
    bubble.className =
      kind === "user"
        ? "rounded-4 px-3 py-2 shadow-sm bg-primary text-white"
        : kind === "error"
          ? "rounded-4 px-3 py-2 border border-danger bg-danger-subtle text-danger-emphasis shadow-sm"
          : "rounded-4 px-3 py-2 shadow-sm bg-white border";

    var label = document.createElement("div");
    label.className =
      "small fw-semibold mb-1 " +
      (kind === "user" ? "text-white-50" : kind === "error" ? "" : "text-primary");
    label.textContent =
      kind === "user"
        ? "You"
        : kind === "error"
          ? "Notice"
          : "Assistant";

    var body = document.createElement("div");
    body.className = kind === "user" ? "" : "text-dark";
    body.style.whiteSpace = "pre-wrap";
    body.innerText = bodyText;

    bubble.appendChild(label);
    bubble.appendChild(body);

    outer.appendChild(bubble);
    transcript.appendChild(outer);

    scrollToBottom();
  }

  function thinkingRowHtml() {
    return (
      '<div class="d-flex align-items-center gap-2 text-muted">' +
      '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>' +
      '<span>Assistant is thinking…</span>' +
      '</div>'
    );
  }

  function showThinkingBubble() {
    if (!transcript) return null;
    removeEmptyState();

    var row = document.createElement("div");
    row.id = "chatThinkingBubble";
    row.className = "d-flex justify-content-start mb-3";
    row.setAttribute("role", "status");
    row.setAttribute("aria-live", "polite");

    var inner = document.createElement("div");
    inner.className = "rounded-4 px-3 py-2 border bg-light text-muted";
    inner.style.maxWidth = "78%";
    inner.innerHTML = thinkingRowHtml();

    row.appendChild(inner);
    transcript.appendChild(row);

    scrollToBottom();
    return row;
  }

  function hideThinkingBubble() {
    var t = document.getElementById("chatThinkingBubble");
    if (t) t.remove();
  }

  function formatServerError(payload, statusCode) {
    if (!payload || typeof payload !== "object") {
      return (
        "We could not process that request (" +
        (statusCode || "error") +
        "). Please try again."
      );
    }
    if (payload.detail) return String(payload.detail);
    var errs = payload.errors;
    if (errs && typeof errs === "object") {
      var parts = [];
      Object.keys(errs).forEach(function (k) {
        parts.push(String(errs[k]));
      });
      if (parts.length) return parts.join(" ");
    }
    return "Something went wrong. Please try again.";
  }

  async function sendPayload(textRaw) {
    var text = (textRaw || "").trim();
    if (!text || !sessionInput || busy) return;

    sendBtn && sendBtn.blur();

    hideThinkingBubble();
    appendBubble("user", text);

    setBusy(true);
    announce("Sending message.");

    hideThinkingBubble();
    showThinkingBubble();
    if (statusLine)
      statusLine.innerHTML =
        '<span class="spinner-border spinner-border-sm me-1" role="status"></span>' +
        '<span class="text-muted small">Assistant is thinking…</span>';

    try {
      var pk = parseInt(sessionInput.value, 10);
      var result = await chatPost(postMessageUrl, {
        session_id: pk,
        message: text,
      });

      hideThinkingBubble();

      if (!result.ok) {
        announce("Unable to fetch reply.");
        appendBubble("error", formatServerError(result.data, result.status));
        scrollToBottom();
        return;
      }

      announce("Assistant responded.");
      var reply = "";
      if (result.data && result.data.message) reply = String(result.data.message);

      appendBubble("assistant", reply || "(Empty reply)");
      textarea.value = "";

      scrollToBottom();
    } catch (e) {
      hideThinkingBubble();
      announce("Network error.");
      appendBubble(
        "error",
        "We could not reach the server. Check your connection and try again.",
      );
    } finally {
      setBusy(false);
      hideThinkingBubble();
      if (statusLine) statusLine.innerHTML = "";
      announce("");
    }
  }

  async function handleNewChat() {
    if (busy) return;
    setBusy(true);
    hideThinkingBubble();
    announce("Starting new conversation.");

    try {
      var res = await chatPost(newSessionUrl, {});
      if (!res.ok) {
        appendBubble("error", formatServerError(res.data, res.status));
        return;
      }
      var sid = res.data && res.data.session_id;
      if (sid == null) {
        appendBubble("error", "Could not start a new chat session.");
        return;
      }

      window.location.href = chatHomeUrl + "?session=" + encodeURIComponent(String(sid));
    } catch (e) {
      appendBubble(
        "error",
        "We could not start a new conversation. Try again shortly.",
      );
    } finally {
      setBusy(false);
      announce("");
    }
  }

  function wireSuggestions() {
    var buttons = root.querySelectorAll(".chat-suggestion");
    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var txt = btn.getAttribute("data-question") || btn.textContent || "";
        textarea.value = txt.trim();
        sendPayload(textarea.value);
      });
    });
  }

  if (sendBtn) {
    sendBtn.addEventListener("click", function () {
      sendPayload(textarea.value);
    });
  }

  if (newChatBtn) {
    newChatBtn.addEventListener("click", function () {
      handleNewChat();
    });
  }

  if (textarea) {
    textarea.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" && !ev.shiftKey) {
        ev.preventDefault();
        sendPayload(textarea.value);
      }
    });
  }

  wireSuggestions();
})();
