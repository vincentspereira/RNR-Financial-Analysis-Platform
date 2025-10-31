/**
 * Tests for LoginForm component
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, createMockUser } from '@/tests/setup';
import { LoginForm } from './LoginForm';
import toast from 'react-hot-toast';

// Mock the API service
vi.mock('@/services/api', () => ({
  apiService: {
    auth: {
      login: vi.fn(),
    },
  },
}));

// Mock react-hot-toast
vi.mock('react-hot-toast');

// Import the mocked API service
import { apiService } from '@/services/api';

describe('LoginForm', () => {
  const user = userEvent.setup();
  const mockLogin = vi.mocked(apiService.auth.login);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders login form with all required fields', () => {
    renderWithProviders(<LoginForm />);

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByText(/don't have an account/i)).toBeInTheDocument();
  });

  it('displays validation errors for empty fields', async () => {
    renderWithProviders(<LoginForm />);

    const submitButton = screen.getByRole('button', { name: /sign in/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
  });

  it('displays validation error for invalid email format', async () => {
    renderWithProviders(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await user.type(emailInput, 'invalid-email');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument();
    });
  });

  it('submits form with valid credentials', async () => {
    const mockUser = createMockUser();
    mockLogin.mockResolvedValue({
      user: mockUser,
      access_token: 'mock-token',
      refresh_token: 'mock-refresh-token',
    });

    renderWithProviders(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
    });
  });

  it('displays error message on login failure', async () => {
    const errorMessage = 'Invalid credentials';
    mockLogin.mockRejectedValue(new Error(errorMessage));

    renderWithProviders(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'wrongpassword');
    await user.click(submitButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(errorMessage);
    });
  });

  it('shows loading state during form submission', async () => {
    // Mock a delayed response
    mockLogin.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

    renderWithProviders(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');
    await user.click(submitButton);

    // Check for loading state
    expect(screen.getByText(/signing in/i)).toBeInTheDocument();
    expect(submitButton).toBeDisabled();

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText(/signing in/i)).not.toBeInTheDocument();
    });
  });

  it('toggles password visibility', async () => {
    renderWithProviders(<LoginForm />);

    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
    const toggleButton = screen.getByRole('button', { name: /toggle password visibility/i });

    // Initially password should be hidden
    expect(passwordInput.type).toBe('password');

    // Click to show password
    await user.click(toggleButton);
    expect(passwordInput.type).toBe('text');

    // Click to hide password again
    await user.click(toggleButton);
    expect(passwordInput.type).toBe('password');
  });

  it('navigates to register page when clicking sign up link', async () => {
    const mockNavigate = vi.fn();
    vi.mock('react-router-dom', async () => {
      const actual = await vi.importActual('react-router-dom');
      return {
        ...actual,
        useNavigate: () => mockNavigate,
      };
    });

    renderWithProviders(<LoginForm />);

    const signUpLink = screen.getByText(/sign up/i);
    await user.click(signUpLink);

    expect(mockNavigate).toHaveBeenCalledWith('/register');
  });

  it('handles keyboard navigation correctly', async () => {
    renderWithProviders(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    // Tab through form elements
    await user.tab();
    expect(emailInput).toHaveFocus();

    await user.tab();
    expect(passwordInput).toHaveFocus();

    await user.tab();
    expect(submitButton).toHaveFocus();
  });

  it('remembers user preference for "Remember me" checkbox', async () => {
    renderWithProviders(<LoginForm />);

    const rememberMeCheckbox = screen.getByLabelText(/remember me/i);

    // Initially unchecked
    expect(rememberMeCheckbox).not.toBeChecked();

    // Check the checkbox
    await user.click(rememberMeCheckbox);
    expect(rememberMeCheckbox).toBeChecked();

    // Uncheck the checkbox
    await user.click(rememberMeCheckbox);
    expect(rememberMeCheckbox).not.toBeChecked();
  });

  it('prevents form submission when already submitting', async () => {
    // Mock a delayed response
    mockLogin.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

    renderWithProviders(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');

    // Submit form
    await user.click(submitButton);

    // Try to submit again while first submission is in progress
    await user.click(submitButton);

    // Should only be called once
    expect(mockLogin).toHaveBeenCalledTimes(1);
  });

  it('clears form errors when user starts typing', async () => {
    renderWithProviders(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    // Submit empty form to trigger validation errors
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    });

    // Start typing in email field
    await user.type(emailInput, 'test');

    // Error should be cleared
    await waitFor(() => {
      expect(screen.queryByText(/email is required/i)).not.toBeInTheDocument();
    });
  });

  it('handles API error responses correctly', async () => {
    const apiError = {
      response: {
        data: {
          error: {
            code: 'AUTH_001',
            message: 'Invalid credentials',
            details: {}
          }
        }
      }
    };

    mockLogin.mockRejectedValue(apiError);

    renderWithProviders(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'wrongpassword');
    await user.click(submitButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Invalid credentials');
    });
  });
});