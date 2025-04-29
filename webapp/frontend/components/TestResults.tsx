import React from 'react';
import { TestResult } from '../types';

interface TestResultsProps {
    results: TestResult[];
}

const TestResults: React.FC<TestResultsProps> = ({ results }) => {
    return (
        <div className="test-results">
            <h2>Test Results</h2>
            <div className="results-grid">
                {results.map(result => (
                    <div key={result.test_id} className={`result-card ${result.status}`}>
                        <h3>{result.test_name}</h3>
                        <div className="result-status">
                            <span className={`status-indicator ${result.status}`} />
                            {result.status.toUpperCase()}
                        </div>
                        {result.error ? (
                            <div className="error-message">{result.error}</div>
                        ) : (
                            <div className="result-details">
                                {Object.entries(result.result).map(([key, value]) => (
                                    <div key={key} className="detail-item">
                                        <span className="detail-label">{key}:</span>
                                        <span className="detail-value">
                                            {typeof value === 'object' 
                                                ? JSON.stringify(value, null, 2)
                                                : String(value)
                                            }
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                        <div className="result-timestamp">
                            {new Date(result.timestamp).toLocaleString()}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};