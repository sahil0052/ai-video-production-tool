import { render, screen } from "@testing-library/react";

import { ProcessingView } from "./ProcessingView";


test("shows the active processing stage and real progress", () => {
  render(
    <ProcessingView
      filename="0806.mp4"
      previewUrl="blob:preview"
      state="transcribing"
      progress={24}
    />
  );

  expect(
    screen.getByRole("heading", { name: "Transcribing speech" })
  ).toBeInTheDocument();
  expect(screen.getByText("24%")).toBeInTheDocument();
  expect(screen.getByText("0806.mp4")).toBeInTheDocument();
});


test("shows semantic asset sourcing as a real pipeline stage", () => {
  render(
    <ProcessingView
      filename="0806.mp4"
      previewUrl="blob:preview"
      state="sourcing"
      progress={50}
    />
  );

  expect(
    screen.getByRole("heading", { name: "Matching visuals and graphics" })
  ).toBeInTheDocument();
});
