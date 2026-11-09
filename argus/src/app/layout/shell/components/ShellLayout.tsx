import { createSignal } from "solid-js";
import { Header } from "./header";
import { LeftPanel } from "./panels/LeftPanel";
import { RightPanel } from "./panels/RightPanel";
import { CentralPanel } from "./panels/CentralPanel";
import { Footer } from "./footer";
import { HeaderProvider } from "../providers/HeaderProvider";
import { BottomPanel, hasVisibleBottomPanels } from "./panels/BottomPanel";

export function ShellLayout() {
  const [bottomHeight, setBottomHeight] = createSignal(
    window.innerHeight * 0.3,
  );
  const [isDragging, setIsDragging] = createSignal(false);

  const startDrag = (e: MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);

    const onMouseMove = (moveEvent: MouseEvent) => {
      const newHeight = window.innerHeight - moveEvent.clientY;

      setBottomHeight(
        Math.max(100, Math.min(newHeight, window.innerHeight * 0.8)),
      );
    };

    const onMouseUp = () => {
      setIsDragging(false);
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  };

  return (
    <div class="h-screen w-screen flex flex-col bg-bg text-fg overflow-hidden">
      <HeaderProvider>
        <Header />
      </HeaderProvider>

      <div class="flex-1 flex overflow-hidden">
        <LeftPanel />

        <main class="flex-1 flex flex-col min-w-0 bg-bg relative">
          <div class="flex-1 overflow-hidden min-h-0">
            <CentralPanel />
          </div>

          <div
            class="flex-col w-full shrink-0"
            style={{ display: hasVisibleBottomPanels() ? "flex" : "none" }}
          >
            <div
              onMouseDown={startDrag}
              class={`relative w-full h-0 cursor-row-resize z-100 shrink-0
                      before:content-[''] before:absolute before:-top-px before:left-0 before:right-0 before:transition-all before:duration-150
                      after:content-[''] after:absolute after:-top-2 after:-bottom-2 after:left-0 after:right-0
                      ${
                        isDragging()
                          ? "border-transparent before:h-0.75 before:bg-sidebar-active"
                          : "border-t border-border before:h-0 hover:border-transparent hover:before:h-0.75 hover:before:bg-sidebar-active"
                      }`}
            />
            <div
              style={{ height: `${bottomHeight()}px` }}
              class="shrink-0 w-full overflow-hidden"
            >
              <BottomPanel />
            </div>
          </div>
        </main>

        <RightPanel />
      </div>

      <Footer />
    </div>
  );
}
