import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LoadsPage from "@/app/loads/page";

// Mock next/navigation
const mockPush = jest.fn();
const mockReplace = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  usePathname: () => "/loads",
}));

// Mock next/link
jest.mock("next/link", () => {
  const MockLink = ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>;
  MockLink.displayName = "MockLink";
  return { __esModule: true, default: MockLink };
});

// Mock lucide-react
jest.mock("lucide-react", () => ({
  Plus: () => <span data-testid="plus-icon">+</span>,
}));

// Mock the API client
const mockGet = jest.fn();
jest.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: jest.fn(),
    setTokens: jest.fn(),
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

import { AuthProvider } from "@/lib/auth";

const MOCK_LOADS = [
  {
    id: "load-1",
    organization_id: "org-1",
    broker_id: null,
    reference_number: "REF-001",
    shipping_document_number: null,
    commodity: "Electronics",
    weight_lbs: 10000,
    pieces: 5,
    rate_total: 2500,
    rate_type: "flat",
    miles_loaded: 500,
    miles_deadhead_est: null,
    notes: null,
    status: "booked",
    stops: [],
    assignments: [],
    created_at: "2026-03-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
  {
    id: "load-2",
    organization_id: "org-1",
    broker_id: null,
    reference_number: "REF-002",
    shipping_document_number: null,
    commodity: "Furniture",
    weight_lbs: 8000,
    pieces: 3,
    rate_total: 1800,
    rate_type: "flat",
    miles_loaded: 350,
    miles_deadhead_est: null,
    notes: null,
    status: "in_transit",
    stops: [],
    assignments: [],
    created_at: "2026-03-05T00:00:00Z",
    updated_at: "2026-03-05T00:00:00Z",
  },
];

function renderLoadsPage() {
  // AuthProvider calls api.get("/api/auth/me") on mount -- return a logged-in user
  mockGet.mockImplementation((path: string) => {
    if (path === "/api/auth/me") {
      return Promise.resolve({
        id: "u1",
        email: "test@example.com",
        roles: ["admin"],
      });
    }
    if (path.startsWith("/api/loads")) {
      return Promise.resolve(MOCK_LOADS);
    }
    return Promise.reject(new Error(`Unexpected GET ${path}`));
  });

  return render(
    <AuthProvider>
      <LoadsPage />
    </AuthProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
});

describe("LoadsPage", () => {
  it("renders the page heading", async () => {
    renderLoadsPage();
    expect(await screen.findByText("Loads")).toBeInTheDocument();
  });

  it("renders a New Load link", async () => {
    renderLoadsPage();
    expect(await screen.findByText("New Load")).toBeInTheDocument();
  });

  it("displays loads in a table after fetching", async () => {
    renderLoadsPage();

    // Wait for load data to appear
    expect(await screen.findByText("REF-001")).toBeInTheDocument();
    expect(screen.getByText("Electronics")).toBeInTheDocument();
    expect(screen.getByText("REF-002")).toBeInTheDocument();
    expect(screen.getByText("Furniture")).toBeInTheDocument();
  });

  it("renders status badges", async () => {
    renderLoadsPage();

    expect(await screen.findByText("booked")).toBeInTheDocument();
    expect(screen.getByText("in transit")).toBeInTheDocument();
  });

  it("renders the status filter dropdown", async () => {
    renderLoadsPage();

    const select = await screen.findByDisplayValue("All statuses");
    expect(select).toBeInTheDocument();
  });

  it("calls the API with a status filter when changed", async () => {
    renderLoadsPage();

    const user = userEvent.setup();

    const select = await screen.findByDisplayValue("All statuses");
    await user.selectOptions(select, "dispatched");

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith("/api/loads?status=dispatched");
    });
  });

  it("shows empty state when no loads are returned", async () => {
    mockGet.mockImplementation((path: string) => {
      if (path === "/api/auth/me") {
        return Promise.resolve({
          id: "u1",
          email: "test@example.com",
          roles: ["admin"],
        });
      }
      if (path.startsWith("/api/loads")) {
        return Promise.resolve([]);
      }
      return Promise.reject(new Error(`Unexpected GET ${path}`));
    });

    render(
      <AuthProvider>
        <LoadsPage />
      </AuthProvider>,
    );

    expect(await screen.findByText("No loads found")).toBeInTheDocument();
  });
});
