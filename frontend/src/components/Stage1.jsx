import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage1.css';

export default function Stage1({ responses }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!responses || responses.length === 0) {
    return null;
  }

  return (
    <div className="stage stage1">
      <h3 className="stage-title">Stage 1: Individual Responses</h3>

      <div className="tabs">
        {responses.map((resp, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {resp.member_name || resp.member || (resp.model && (resp.model.split('/')[1] || resp.model))}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="model-name">
          {responses[activeTab].member_name || responses[activeTab].member || responses[activeTab].model}
          {responses[activeTab].role && (
            <div className="model-role">{responses[activeTab].role}</div>
          )}
        </div>
        <div className="response-text markdown-content">
          <ReactMarkdown>{responses[activeTab].response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
