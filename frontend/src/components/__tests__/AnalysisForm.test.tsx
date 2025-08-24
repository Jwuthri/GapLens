import { render, screen, fireEvent } from '@testing-library/react';
import AnalysisForm from '../AnalysisForm';

// Mock the validation utility
jest.mock('@/utils/validation', () => ({
  validateInput: jest.fn((input: string) => {
    if (!input.trim()) {
      return { isValid: false, error: 'Please enter a URL or app ID' };
    }
    if (input.includes('play.google.com')) {
      return { isValid: true, type: 'APP', platform: 'GOOGLE_PLAY' };
    }
    return { isValid: true, type: 'WEBSITE' };
  }),
}));

describe('AnalysisForm', () => {
  const mockOnSubmit = jest.fn();

  beforeEach(() => {
    mockOnSubmit.mockClear();
  });

  it('renders form elements correctly', () => {
    render(<AnalysisForm onSubmit={mockOnSubmit} isLoading={false} />);
    
    expect(screen.getByText('App Store Analysis')).toBeInTheDocument();
    expect(screen.getByText('Website Analysis')).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /start analysis/i })).toBeInTheDocument();
  });

  it('switches analysis type when buttons are clicked', () => {
    render(<AnalysisForm onSubmit={mockOnSubmit} isLoading={false} />);
    
    const websiteButton = screen.getByText('Website Analysis');
    fireEvent.click(websiteButton);
    
    expect(screen.getByPlaceholderText(/example.com/)).toBeInTheDocument();
  });

  it('shows error for empty input', () => {
    render(<AnalysisForm onSubmit={mockOnSubmit} isLoading={false} />);
    
    const input = screen.getByRole('textbox');
    
    // Add some text first to enable the button, then clear it and submit via form
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.change(input, { target: { value: '   ' } }); // whitespace only
    
    const form = input.closest('form');
    fireEvent.submit(form!);
    
    expect(screen.getByText('Please enter a URL or app ID')).toBeInTheDocument();
  });

  it('disables form when loading', () => {
    render(<AnalysisForm onSubmit={mockOnSubmit} isLoading={true} />);
    
    const input = screen.getByRole('textbox');
    const submitButton = screen.getByRole('button', { name: /analyzing/i });
    
    expect(input).toBeDisabled();
    expect(submitButton).toBeDisabled();
  });
});