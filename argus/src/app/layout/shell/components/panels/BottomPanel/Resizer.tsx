/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal } from "solid-js";

export const Resizer = (props: {
  getContainerRef: () => HTMLDivElement | undefined;
  onWidthChange: (width: number) => void;
}) => {
  const [isDragging, setIsDragging] = createSignal(false);

  const startDrag = (e: MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const onMouseMove = (moveEvent: MouseEvent) => {
      const containerRef = props.getContainerRef();
      if (!containerRef) return;

      const rect = containerRef.getBoundingClientRect();
      const newPercentage =
        ((moveEvent.clientX - rect.left) / rect.width) * 100;
      props.onWidthChange(Math.max(15, Math.min(newPercentage, 85)));
    };

    const onMouseUp = () => {
      setIsDragging(false);
      document.body.style.cursor = "auto";
      document.body.style.userSelect = "auto";
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  };

  return (
    <div
      onMouseDown={startDrag}
      class={`relative h-full w-px cursor-col-resize z-50 shrink-0 bg-border
             before:content-[''] before:absolute before:inset-0 before:transition-all before:duration-150
             after:content-[''] after:absolute after:-left-2 after:-right-2 after:top-0 after:bottom-0
             ${isDragging() ? "before:bg-sidebar-active before:-left-0.5 before:-right-0.5" : "hover:before:bg-sidebar-active hover:before:-left-0.5 hover:before:-right-0.5"}`}
    />
  );
};
