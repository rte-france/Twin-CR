/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export interface ResettableMock {
  reset(): void;
}

export interface MockRegistry {
  handlers: Record<string, (args: any) => any>;
  resetAll(): void;
  register(mock: ResettableMock, handlers: Record<string, (args: any) => any>): void;
}

export const createMockRegistry = (): MockRegistry => {
  const resettables = new Set<ResettableMock>();
  const allHandlers: Record<string, (args: any) => any> = {};

  return {
    handlers: allHandlers,
    register(mock: ResettableMock, handlers: Record<string, (args: any) => any>) {
      resettables.add(mock);
      Object.assign(allHandlers, handlers);
    },
    resetAll() {
      for (const mock of resettables) {
        mock.reset();
      }
    },
  };
};
