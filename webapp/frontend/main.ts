interface Camera {
    id: string;
    name: string;
    interface: string;
}

interface TestResult {
    testName: string;
    status: 'success' | 'error' | 'warning';
    message: string;
    timestamp: string;
}

class GenICamTester {
    private apiUrl = 'http://localhost:8000/api';

    async detectCameras(): Promise<Camera[]> {
        try {
            const response = await fetch(`${this.apiUrl}/cameras`);
            const data = await response.json();
            return data.cameras;
        } catch (error) {
            console.error('Error detecting cameras:', error);
            return [];
        }
    }

    async runTest(cameraId: string, testType: string): Promise<TestResult> {
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

    async runSelectedTests(cameraId: string, selectedTests: string[]): Promise<TestResult[]> {
        const results: TestResult[] = [];
        for (const test of selectedTests) {
            const result = await this.runTest(cameraId, test);
            results.push(result);
        }
        return results;
    }
}

// UI Controller
class UIController {
    private tester: GenICamTester;
    private selectedCamera: string | null = null;

    constructor() {
        this.tester = new GenICamTester();
        this.initializeEventListeners();
    }

    private initializeEventListeners(): void {
        document.getElementById('detectCameras')?.addEventListener('click', () => this.detectCameras());
        document.getElementById('startTests')?.addEventListener('click', () => this.startTests());
        document.getElementById('viewResults')?.addEventListener('click', () => this.viewResults());
    }

    private async detectCameras(): Promise<void> {
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

    private async startTests(): Promise<void> {
        if (!this.selectedCamera) {
            alert('Please select a camera first');
            return;
        }

        const selectedTests = Array.from(document.querySelectorAll('input[type="checkbox"]:checked'))
            .map(cb => (cb as HTMLInputElement).id.replace('test-', ''));

        const results = await this.tester.runSelectedTests(this.selectedCamera, selectedTests);
        this.displayResults(results);
    }

    private displayResults(results: TestResult[]): void {
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

    private viewResults(): void {
        document.getElementById('results')?.scrollIntoView({ behavior: 'smooth' });
    }

    public selectCamera(cameraId: string): void {
        this.selectedCamera = cameraId;
        document.querySelectorAll('.camera-item').forEach(item => 
            item.classList.toggle('selected', (item as HTMLElement).dataset.id === cameraId)
        );
    }
}

// Initialize the application
const app = new UIController();
(window as any).selectCamera = (cameraId: string) => app.selectCamera(cameraId);