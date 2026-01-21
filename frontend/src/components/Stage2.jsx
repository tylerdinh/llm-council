import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage2.css';

export default function Stage2({ collaboration }) {
  const [selectedRound, setSelectedRound] = useState(1);

  if (!collaboration || collaboration.length === 0) {
    return (
      <div className="stage stage2">
        <h3>Stage 2: Collaboration</h3>
        <p className="no-data">No collaboration exchanges occurred.</p>
      </div>
    );
  }

  // Group entries by round
  const rounds = {};
  collaboration.forEach(entry => {
    const round = entry.round || 1;
    if (!rounds[round]) {
      rounds[round] = [];
    }
    rounds[round].push(entry);
  });

  const roundNumbers = Object.keys(rounds).sort((a, b) => a - b);
  const currentRoundEntries = rounds[selectedRound] || [];

  return (
    <div className="stage stage2">
      <h3>Stage 2: Collaboration</h3>
      <p className="stage-description">
        Council members engage in discussion through tool-based messaging.
      </p>

      {/* Round selector */}
      {roundNumbers.length > 1 && (
        <div className="round-selector">
          {roundNumbers.map(round => (
            <button
              key={round}
              className={`round-button ${selectedRound === parseInt(round) ? 'active' : ''}`}
              onClick={() => setSelectedRound(parseInt(round))}
            >
              Round {round}
            </button>
          ))}
        </div>
      )}

      {/* Display collaboration entries for selected round */}
      <div className="collaboration-log">
        {currentRoundEntries.map((entry, idx) => {
          if (entry.type === 'message_delivery') {
            // Inter-member message
            return (
              <div key={idx} className="collaboration-entry message-delivery">
                <div className="message-header">
                  <span className="from-member">{entry.from}</span>
                  <span className="arrow">→</span>
                  <span className="to-member">{entry.to}</span>
                </div>
                <div className="message-text markdown-content">
                  <ReactMarkdown>{entry.message}</ReactMarkdown>
                </div>
              </div>
            );
          } else {
            // Member thinking/response
            return (
              <div key={idx} className="collaboration-entry member-response">
                <div className="member-header">
                  <strong>{entry.member_name}</strong>
                </div>
                {entry.content && (
                  <div className="member-content markdown-content">
                    <ReactMarkdown>{entry.content}</ReactMarkdown>
                  </div>
                )}
                {entry.tool_calls && entry.tool_calls.length > 0 && (
                  <div className="tool-calls">
                    {entry.tool_calls.map((tc, tcIdx) => (
                      <div key={tcIdx} className="tool-call">
                        <span className="tool-name">🔧 {tc.tool}</span>
                        {tc.arguments && (
                          <div className="tool-args">
                            {tc.arguments.to_member && (
                              <span>To: {tc.arguments.to_member}</span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          }
        })}
      </div>
    </div>
  );
}
