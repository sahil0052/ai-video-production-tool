import { fireEvent, render, screen } from "@testing-library/react";

import { ResultView } from "./ResultView";


test("shows the finished player and download action", () => {
  const onReset = vi.fn();
  render(
    <ResultView
      filename="0806.mp4"
      videoUrl="/api/jobs/example/video"
      captionCount={12}
      cutCount={5}
      brollCoverage={0.6}
      styleScore={90}
      qcPassed={true}
      onReset={onReset}
    />
  );

  expect(screen.getByLabelText("Edited video preview")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Download MP4" })).toHaveAttribute(
    "href",
    "/api/jobs/example/video"
  );
  expect(screen.getByText("12 caption beats")).toBeInTheDocument();
  expect(screen.getByText("60% visual coverage")).toBeInTheDocument();
  expect(screen.getByText("90 / 100")).toBeInTheDocument();
  expect(screen.getByText("QC passed")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Edit another video" }));
  expect(onReset).toHaveBeenCalledOnce();
});
