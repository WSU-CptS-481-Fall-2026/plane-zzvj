import type { ComponentProps } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TourRoot } from "@/components/onboarding/tour/root";

const { createProject } = vi.hoisted(() => ({ createProject: vi.fn() }));

vi.mock("@/hooks/store/use-command-palette", () => ({
  useCommandPalette: () => ({ toggleCreateProjectModal: createProject }),
}));
vi.mock("@/hooks/store/user", () => ({ useUser: () => ({ data: { first_name: "Test", last_name: "User" } }) }));
vi.mock("@makeplane/propel/components/button", () => ({
  Button: ({ label, onClick }: { label: string; onClick: ComponentProps<"button">["onClick"] }) => (
    <button type="button" onClick={onClick}>
      {label}
    </button>
  ),
}));
vi.mock("@plane/blocks/icons", () => ({ PlaneLockup: () => <span /> }));
vi.mock("@makeplane/propel/icons", () => ({
  CloseOutline: () => <span data-testid="close-tour" />,
  CyclesOutline: () => <span />,
  ModuleOutline: () => <span />,
  PagesOutline: () => <span />,
  ViewsOutline: () => <span />,
  WorkItemsOutline: () => <span />,
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const startTour = () => fireEvent.click(screen.getByRole("button", { name: "Take a Product Tour" }));

describe("#7447 onboarding wording", () => {
  it("shows the corrected work-item description", () => {
    render(<TourRoot onComplete={vi.fn()} />);
    startTour();
    expect(
      screen.getByText(
        "The work item is the building block of Plane. Most concepts in Plane are associated with work items and their properties."
      )
    ).toBeTruthy();
  });

  it("keeps Next, Back, sidebar navigation and project creation working", () => {
    const onComplete = vi.fn();
    render(<TourRoot onComplete={onComplete} />);
    startTour();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("heading", { name: "Move with cycles" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByRole("heading", { name: "Plan with work items" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Pages" }));
    fireEvent.click(screen.getByRole("button", { name: "Create your first project" }));
    expect(onComplete).toHaveBeenCalledOnce();
    expect(createProject).toHaveBeenCalledWith(true);
  });

  it("keeps skipping and closing the tour working", () => {
    const onComplete = vi.fn();
    render(<TourRoot onComplete={onComplete} />);
    fireEvent.click(screen.getByRole("button", { name: "No thanks, I will explore it myself" }));
    expect(onComplete).toHaveBeenCalledOnce();
    startTour();
    fireEvent.click(screen.getByTestId("close-tour").closest("button")!);
    expect(onComplete).toHaveBeenCalledTimes(2);
  });
});
