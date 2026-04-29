import { useState } from 'react';

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState('');

  function handleSubmit(e) {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText('');
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSubmit(e);
    }
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about proteins, sequences, or literature... (Enter to send, Shift+Enter for newline)"
        rows={2}
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || !text.trim()}>
        {disabled ? '...' : 'Send'}
      </button>
    </form>
  );
}
