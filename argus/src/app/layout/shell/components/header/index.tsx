/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Show, onMount, onCleanup, type Component } from "solid-js";
import { useHeader } from "../../providers/HeaderProvider";
import { useAppWindow } from "./hooks/useAppWindow";
import { ToolsMenu } from "./components/ToolsMenu";
import { CentralMenu } from "./components/CenterMenu";
import { LeftMenu } from "./components/LeftMenu";
import { RightMenu } from "./components/RightMenu";

const isInteractiveElement = (target: HTMLElement): boolean => {
  const interactiveSelectors = [
    "button",
    '[role="button"]',
    "select",
    "input",
    "[data-no-drag]",
    '[role="menubar"]',
    '[role="menu"]',
    '[role="menuitem"]',
  ];
  return interactiveSelectors.some((selector) => !!target.closest(selector));
};

const HeaderContent: Component<{
  onMouseDown: (e: MouseEvent) => void;
  onOpenMenus: () => void;
}> = (props) => {
  const stopPropagation = (e: MouseEvent) => e.stopPropagation();

  return (
    <div class="bg-bg border-b border-border w-full h-8 outline-none">
      <div
        class="w-full h-8 flex items-center header-glass z-10 outline-none"
        onMouseDown={(e) => props.onMouseDown(e)}
      >
        <div
          class="relative flex-1 flex justify-start h-full items-center pl-2 outline-none"
          onMouseDown={stopPropagation}
        >
          <LeftMenu onOpenMenus={props.onOpenMenus} />
        </div>

        <div class="relative flex-1 h-full cursor-grab outline-none">
          &nbsp;
        </div>

        <div
          class="relative flex justify-center items-center px-4 outline-none"
          onMouseDown={stopPropagation}
        >
          <CentralMenu />
        </div>

        <div class="relative flex-1 h-full cursor-grab outline-none">
          &nbsp;
        </div>

        <div
          class="relative flex-1 flex justify-end h-full outline-none"
          onMouseDown={stopPropagation}
        >
          <RightMenu />
        </div>
      </div>
    </div>
  );
};

export const Header: Component = () => {
  const { isOpen, setOpen } = useHeader();
  const { toggleMaximize, startDragging } = useAppWindow();

  let headerRef: HTMLDivElement | undefined;

  onMount(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (!isOpen() || !headerRef) return;

      const target = e.target as HTMLElement;

      if (headerRef.contains(target)) return;

      if (
        target.closest(
          '[role="menu"], [role="menuitem"], [data-kb-popper-content-host]',
        )
      ) {
        return;
      }

      setOpen(false);
    };

    document.addEventListener("mousedown", handleClickOutside);
    onCleanup(() =>
      document.removeEventListener("mousedown", handleClickOutside),
    );
  });

  const handleDragStart = async (e: MouseEvent) => {
    const target = e.target as HTMLElement;
    if (isInteractiveElement(target)) return;
    if (e.buttons !== 1) return;

    if (e.detail === 2) {
      await toggleMaximize();
    } else {
      await startDragging();
    }
  };

  return (
    <header ref={headerRef} class="select-none font-sans outline-none">
      <Show
        when={isOpen()}
        fallback={
          <HeaderContent
            onMouseDown={handleDragStart}
            onOpenMenus={() => setOpen(true)}
          />
        }
      >
        <ToolsMenu />
      </Show>
    </header>
  );
};
