import React, { useState } from 'react';
import { Camera, TestConfig, TestResult } from '../types';

interface TestPanelProps {
    camera: Camera;
    onTestComplete: (results: TestResult[]) => void;
}

const testCategories = {
    basic: {
        title: "Basic Tests",
        tests: [
            { id: 'initialization', name: 'Camera Initialization', default: true },
            { id: 'image_acquisition', name: 'Image Acquisition', default: true },
            { id: 'feature_access', name: 'Feature Access', default: true },
        ]
    },
    functional: {
        title: "Functional Tests",
        tests: [
            { id: 'blur_detection', name: 'Blur Detection', default: false },
            { id: 'edge_detection', name: 'Edge Detection', default: false },
            { id: 'camera_calibration', name: 'Camera Calibration', default: false },
        ]
    },
    performance: {
        title: "Performance Tests",
        tests: [
            { id: 'long_run', name: 'Long Run Test', default: false },
            { id: 'max_fps', name: 'Max FPS Test', default: false },
            { id: 'power_cycle', name: 'Power Cycle Test', default: false },
        ]
    },
    advanced: {
        title: "Advanced Tests",
        tests: [
            { id: 'multicam', name: 'Multi-Camera Test', default: false },
            { id: 'roi', name: 'ROI Testing', default: false },
            { id: 'io_test', name: 'I/O Test', default: false },
            { id: 'image_quality', name: 'Image Quality', default: true },
        ]
    }
};

const TestPanel: React.FC<TestPanelProps> = ({ camera, onTestComplete }) => {
    const [selectedTests, setSelectedTests] = useState<string[]>(
        Object.values(testCategories)
            .flatMap(category => category.tests)
            .filter(test => test.default)
            .map(test => test.id)
    );
    const [running, setRunning] = useState(false);
    const [progress, setProgress] = useState<{[key: string]: string}>({});

    const toggleTest = (testId: string) => {
        setSelectedTests(current =>
            current.includes(testId)
                ? current.filter(id => id !== testId)
                : [...current, testId]
        );
    };

    const toggleCategory = (tests: typeof testCategories[keyof typeof testCategories]['tests']) => {
        const testIds = tests.map(t => t.id);
        const allSelected = testIds.every(id => selectedTests.includes(id));
        
        setSelectedTests(current => 
            allSelected
                ? current.filter(id => !testIds.includes(id))
                : [...new Set([...current, ...testIds])]
        );
    };

    const runTests = async () => {
        if (running) return;
        setRunning(true);
        setProgress({});

        try {
            // Setup WebSocket for real-time updates
            const ws = new WebSocket(`ws://localhost:8000/ws/${camera.id}`);
            ws.onmessage = (event) => {
                const update = JSON.parse(event.data);
                if (update.type === 'test_update') {
                    setProgress(prev => ({
                        ...prev,
                        [update.test_name]: update.status
                    }));
                }
            };

            // Run basic tests first
            const basicTestsConfig: TestConfig = {
                camera_id: camera.id,
                tests: selectedTests.filter(test => 
                    testCategories.basic.tests.some(t => t.id === test)
                )
            };
            
            if (basicTestsConfig.tests.length > 0) {
                const basicResponse = await fetch('/api/test/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(basicTestsConfig)
                });
                const basicData = await basicResponse.json();
                if (basicData.status !== 'success') throw new Error('Basic tests failed');
            }

            // Run functional tests
            const functionalTests = selectedTests.filter(test => 
                testCategories.functional.tests.some(t => t.id === test)
            );

            for (const test of functionalTests) {
                await fetch(`/api/functional/${test}/${camera.id}`, {
                    method: 'POST'
                });
            }

            // Run remaining tests
            const remainingTestsConfig: TestConfig = {
                camera_id: camera.id,
                tests: selectedTests.filter(test => 
                    [...testCategories.performance.tests, ...testCategories.advanced.tests]
                        .some(t => t.id === test)
                )
            };

            if (remainingTestsConfig.tests.length > 0) {
                const response = await fetch('/api/test/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(remainingTestsConfig)
                });
                const data = await response.json();
                if (data.status === 'success') {
                    onTestComplete(data.results);
                }
            }

            ws.close();
        } catch (error) {
            console.error('Test execution failed:', error);
        } finally {
            setRunning(false);
        }
    };

    return (
        <div className="test-panel">