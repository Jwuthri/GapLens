import '@testing-library/jest-dom'

// Mock chartjs-adapter-date-fns to avoid date adapter issues in tests
jest.mock('chartjs-adapter-date-fns', () => ({}))

// Mock Chart.js
jest.mock('chart.js', () => ({
  Chart: {
    register: jest.fn(),
  },
  CategoryScale: {},
  LinearScale: {},
  BarElement: {},
  PointElement: {},
  LineElement: {},
  Title: {},
  Tooltip: {},
  Legend: {},
  TimeScale: {},
}))

// Mock react-chartjs-2
jest.mock('react-chartjs-2', () => ({
  Bar: ({ data, options, ...props }) => (
    <div data-testid="bar-chart" data-chart-data={JSON.stringify(data)} {...props}>
      Bar Chart Mock
    </div>
  ),
  Line: ({ data, options, ...props }) => (
    <div data-testid="line-chart" data-chart-data={JSON.stringify(data)} {...props}>
      Line Chart Mock
    </div>
  ),
}))

// Mock URL.createObjectURL and URL.revokeObjectURL
global.URL.createObjectURL = jest.fn(() => 'mocked-url')
global.URL.revokeObjectURL = jest.fn()

// Mock fetch
global.fetch = jest.fn()

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
})