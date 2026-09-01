import { fireEvent, render, screen } from "@testing-library/react";

import { UploadPanel } from "./UploadPanel";


test("rejects non-MP4 files before upload", () => {
  render(<UploadPanel busy={false} onUpload={() => undefined} />);
  const input = screen.getByLabelText("Choose raw MP4 video");
  const file = new File(["notes"], "notes.txt", { type: "text/plain" });

  fireEvent.change(input, { target: { files: [file] } });

  expect(screen.getByRole("alert")).toHaveTextContent("MP4");
});


test("submits a selected MP4 file", () => {
  const onUpload = vi.fn();
  render(<UploadPanel busy={false} onUpload={onUpload} />);
  const input = screen.getByLabelText("Choose raw MP4 video");
  const file = new File(["video"], "0806.mp4", { type: "video/mp4" });

  fireEvent.change(input, { target: { files: [file] } });
  fireEvent.click(screen.getByRole("button", { name: "Edit this video" }));

  expect(onUpload).toHaveBeenCalledWith(file);
});
