class GenICamTester {
    constructor() {
        this.apiUrl = 'http://localhost:8000/api';
    }

    async detectCameras() {
        try {
            const response = await fetch(`${this.apiUrl}/cameras`);
            const data = await response.json();
            return data.cameras;
        } catch (error) {
            console.error('Error detecting cameras:', error);
            return [];
        }
    }

    async runTest(cameraId, testType) {
        try {
            const response = await fetch(`${this.apiUrl}/test/${testType}/${cameraId}`, {
                method: 'POST'
            });
            return await response.json();
        } catch (error) {
            return {
                testName: testType,
                status: 'error',
                message: `Test failed: ${error.message}`,
                timestamp: new Date().toISOString()
            };
        }
    }

    async runSelectedTests(cameraId, selectedTests) {
        const results = [];
        for (const test of selectedTests) {
            const result = await this.runTest(cameraId, test);
            results.push(result);
        }
        return results;
    }
}

class UIController {
    constructor() {
        this.tester = new GenICamTester();
        this.selectedCamera = null;
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        document.getElementById('detectCameras')?.addEventListener('click', () => this.detectCameras());
        document.getElementById('startTests')?.addEventListener('click', () => this.startTests());
        document.getElementById('viewResults')?.addEventListener('click', () => this.viewResults());
    }

    async detectCameras() {
        const cameras = await this.tester.detectCameras();
        const cameraList = document.getElementById('cameras');
        if (!cameraList) return;

        cameraList.innerHTML = cameras.length ? 
            cameras.map(camera => `
                <div class="camera-item" data-id="${camera.id}">
                    <h3>${camera.name}</h3>
                    <p>Interface: ${camera.interface}</p>
                    <button onclick="selectCamera('${camera.id}')">Select</button>
                </div>
            `).join('') :
            '<p>No cameras detected</p>';
    }

    async startTests() {
        if (!this.selectedCamera) {
            alert('Please select a camera first');
            return;
        }

        const selectedTests = Array.from(document.querySelectorAll('input[type="checkbox"]:checked'))
            .map(cb => cb.id.replace('test-', ''));

        const results = await this.tester.runSelectedTests(this.selectedCamera, selectedTests);
        this.displayResults(results);
    }

    displayResults(results) {
        const resultsContainer = document.getElementById('testResults');
        if (!resultsContainer) return;

        resultsContainer.innerHTML = results.map(result => `
            <div class="result-item ${result.status}">
                <h4>${result.testName}</h4>
                <p>${result.message}</p>
                <small>${new Date(result.timestamp).toLocaleString()}</small>
            </div>
        `).join('');
    }

    viewResults() {
        document.getElementById('results')?.scrollIntoView({ behavior: 'smooth' });
    }

    selectCamera(cameraId) {
        this.selectedCamera = cameraId;
        document.querySelectorAll('.camera-item').forEach(item => 
            item.classList.toggle('selected', item.dataset.id === cameraId)
        );
    }
}

// Initialize the application
const app = new UIController();
window.selectCamera = (cameraId) => app.selectCamera(cameraId);