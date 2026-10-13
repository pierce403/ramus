import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import App from "../App";

describe("App", () => {
  it("renders hero heading", () => {
    const { getByRole } = render(<App />);
    expect(getByRole("heading", { level: 1, name: /Ramus, Ancient Tree God/i })).toBeInTheDocument();
  });
});
