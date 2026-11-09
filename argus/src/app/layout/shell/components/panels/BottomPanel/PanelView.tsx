import { FiExternalLink, FiMinus } from "solid-icons/fi";
import { MfeLoader } from "../../MfeLoader";
import { detachPanel, PanelState } from "./utils";

export const PanelView = (props: {
  panel: PanelState;
  class?: string;
  style?: any;
  onClose: () => void;
}) => {
  return (
    <div
      class={`group h-full flex flex-col relative min-w-0 ${props.class || ""}`}
      style={props.style}
    >
      <div class="flex-none h-9 bg-sidebar-bg px-3 flex justify-between items-center border-b border-border z-20">
        <span class="text-xs uppercase font-bold text-sidebar-fg opacity-70 truncate">
          {props.panel.manifest.label}
        </span>

        <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none group-hover:pointer-events-auto">
          <button
            class="p-1 hover:bg-icon-btn-bg-hover rounded transition-all flex items-center justify-center text-sidebar-fg opacity-70 hover:opacity-100"
            onClick={() => detachPanel(props.panel, props.onClose)}
            title="Detach to new window"
          >
            <FiExternalLink class="size-3.5" />
          </button>
          <button
            onClick={props.onClose}
            class="p-1 hover:bg-icon-btn-bg-hover hover:text-red-400 rounded transition-all flex items-center justify-center text-sidebar-fg opacity-70 hover:opacity-100"
            title="Close"
          >
            <FiMinus class="size-3.5" />
          </button>
        </div>
      </div>

      <div class="flex-1 w-full relative min-h-0 overflow-auto">
        <MfeLoader
          manifest={props.panel.manifest}
          componentProps={props.panel.params}
        />
      </div>
    </div>
  );
};
