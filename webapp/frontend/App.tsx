import React, { useState } from 'react';
import CameraList from './components/CameraList';
import LiveView from './components/LiveView';
import TestPanel from './components/TestPanel';
import TestResults from './components/TestResults';
import { Camera, TestResult } from './types';

const App: React.FC = () => {
    const [selectedCamera, setSelectedCamera] = useState<Camera | undefined>(undefined);
    const [testResults, setTestResults] = useState<TestResult[]>([]);

    const handleCameraSelect = (camera: Camera) => {
        setSelectedCamera(camera);
        setTestResults([]); // Clear previous results when selecting a new camera
    };

    const handleTestComplete = (results: TestResult[]) => {
        setTestResults(results);
        // Scroll to results
        document.getElementById('results-section')?.scrollIntoView({ behavior: 'smooth' });
    };

    return (
        <div className="app">
            <header className="app-header">
                <h1>GenICam Tester AI</h1>
            </header>
            
            <main className="app-main">
                <div className="main-container">
                    {/* Camera selection and live view */}
                    <section className="camera-controls">
                        <div className="camera-list-container">
                            <CameraList 
                                onSelectCamera={handleCameraSelect}
                                selectedCamera={selectedCamera}
                            />
                        </div>
                        
                        {selectedCamera && (
                            <div className="camera-view-container">
                                <LiveView camera={selectedCamera} />
                            </div>
                        )}
                    </section>

                    {/* Test controls and results */}
                    {selectedCamera && (
                        <section className="test-controls">
                            <div className="test-panel-container">
                                <TestPanel
                                    camera={selectedCamera}
                                    onTestComplete={handleTestComplete}
                                />
                            </div>
                            
                            {testResults.length > 0 && (
                                <div id="results-section" className="test-results-container">
                                    <TestResults results={testResults} />
                                </div>
                            )}
                        </section>
                    )}
                </div>
            </main>

            <footer className="app-footer">
                <p>© 2025 GenICam Tester AI - Version 1.0.0</p>
            </footer>
        </div>
    );
};

export default App;