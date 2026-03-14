import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LoginPage from "@/app/login/page";

// Mock next/navigation
const mockPush = jest.fn();
const mockReplace = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  usePathname: () => "/login",
}));

// Mock the API client
const mockPost = jest.fn();
const mockGet = jest.fn();
const mockSetTokens = jest.fn();
jest.mock("@/lib/api", () => ({
  api: {
    post: (...args: unknown[]) => mockPost(...args),
    get: (...args: unknown[]) => mockGet(...args),
    setTokens: (...args: unknown[]) => mockSetTokens(...args),
    clearTokens: jest.fn(),
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
}));

// Wrapper that provides AuthProvider (LoginPage uses useAuth)
import { AuthProvider } from "@/lib/auth";

function renderLoginPage() {
  // When AuthProvider mounts, it calls api.get("/api/auth/me").
  // Reject it so user = null and loading = false.
  mockGet.mockRejectedValueOnce(new Error("not logged in"));

  return render(
    <AuthProvider>
      <LoginPage />
    </AuthProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
});

describe("LoginPage", () => {
  it("renders email and password inputs", async () => {
    renderLoginPage();

    expect(
      await screen.findByPlaceholderText("owner@example.com"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("renders the sign-in button", async () => {
    renderLoginPage();

    expect(await screen.findByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("calls the login API on submit", async () => {
    mockPost.mockResolvedValueOnce({
      access_token: "tok_access",
      refresh_token: "tok_refresh",
      token_type: "bearer",
    });

    renderLoginPage();

    // After the initial auth check rejects (set up by renderLoginPage),
    // queue the successful /api/auth/me response for after login.
    mockGet.mockResolvedValueOnce({
      id: "u1",
      email: "test@example.com",
      roles: ["admin"],
    });

    const user = userEvent.setup();

    const emailInput = await screen.findByPlaceholderText("owner@example.com");
    const passwordInput = screen.getByLabelText(/password/i);
    const submitBtn = screen.getByRole("button", { name: /sign in/i });

    await user.type(emailInput, "test@example.com");
    await user.type(passwordInput, "password123");
    await user.click(submitBtn);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith("/api/auth/login", {
        email: "test@example.com",
        password: "password123",
      });
    });

    expect(mockSetTokens).toHaveBeenCalledWith("tok_access", "tok_refresh");
    expect(mockPush).toHaveBeenCalledWith("/dashboard");
  });

  it("displays an error message when login fails", async () => {
    mockPost.mockRejectedValueOnce(new Error("Invalid credentials"));

    renderLoginPage();

    const user = userEvent.setup();

    const emailInput = await screen.findByPlaceholderText("owner@example.com");
    const passwordInput = screen.getByLabelText(/password/i);
    const submitBtn = screen.getByRole("button", { name: /sign in/i });

    await user.type(emailInput, "bad@example.com");
    await user.type(passwordInput, "wrongpass");
    await user.click(submitBtn);

    expect(await screen.findByText("Invalid credentials")).toBeInTheDocument();
  });
});
