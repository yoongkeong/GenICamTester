export interface Camera {
    id: string;
    name: string;
    interface: string;
    model?: string;
}

export interface TestConfig {
    camera_id: string;
    tests: string[];
    parameters?: Record<string, any>;
}

export interface TestResult {
    test_id: string;
    camera_id: string;
    test_name: string;
    status: 'success' | 'error' | 'warning';
    result: Record<string, any>;
    error?: string;
    timestamp: string;
}

export interface TestUpdate {
    type: 'test_update';
    test_name: string;
    status: string;
    message: string;
    data?: Record<string, any>;
    timestamp: string;
}

export interface CameraStatus {
    type: 'camera_status';
    status: string;
    message: string;
    timestamp: string;
}