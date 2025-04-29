import React, { useState } from 'react';
import CameraList from './components/CameraList';
import TestPanel from './components/TestPanel';
import TestResults from './components/TestResults';
import { Camera, TestResult } from './types';

const App: React.FC = () => {
    const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);
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
                <section className="camera-section">
                    <CameraList 
                        onSelectCamera={handleCameraSelect}
                        selectedCamera={selectedCamera}
                    />
                </section>

                {selectedCamera && (
                    <section className="test-section">
                        <TestPanel
                            camera={selectedCamera}
                            onTestComplete={handleTestComplete}
                        />
                    </section>
                )}

                {testResults.length > 0 && (
                    <section id="results-section" className="results-section">
                        <TestResults results={testResults} />
                    </section>
                )}
            </main>

            <footer className="app-footer">
                <p>© 2025 GenICam Tester AI - Version 1.0.0</p>
            </footer>
        </div>
    );
};