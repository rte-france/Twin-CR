API & Service Reference
=======================

This reference chapter collects endpoint summaries, key classes, and helper
functions in a single place. For exhaustive member listings see the auto-doc
sections in :doc:`routers`, :doc:`domain`, :doc:`services`, and
:doc:`utilities`.

HTTP Endpoints
--------------

.. list-table::
   :header-rows: 1
   :widths: 30 10 60

   * - Path
     - Method
     - Purpose
   * - ``/trainer/dsl_command``
     - ``POST``
     - Parse ad-hoc DSL text from a trainer and enqueue events for the active simulation.
   * - ``/trainer/init``
     - ``POST``
     - Upload or reuse IIDM artifacts, parse DSL, and persist the new simulation configuration.
   * - ``/trainer/dsl/simulations``
     - ``GET``
     - List DSL files stored in the DSL bucket (name, path, metadata).
   * - ``/trainer/iidm``
     - ``GET``
     - List IIDM artifacts plus cached metadata and related files.
   * - ``/trainer/dsl/{simulationName}``
     - ``GET`` / ``DELETE`` / ``PUT``
     - Download, remove, or overwrite the DSL file for ``simulationName``.
   * - ``/iidm/upload``
     - ``POST``
     - Store IIDM artifacts in the ClickHouse-backed object store and precompute cached metadata.
   * - ``/iidm/properties/{file_id}``
     - ``GET``
     - Retrieve cached network details.
   * - ``/lsp/completions/keywords``
     - ``GET``
     - Return DSL grammar literals matching an optional completion prefix.
   * - ``/lsp/completions/elements``
     - ``GET``
     - Return matching IIDM element IDs for a component type with artifact-context fallback.
   * - ``/sim/simulatorcontrol``
     - ``POST``
     - Aggregate actions into ``AggregateOutput``.
   * - ``/sim/simulatorcontrol_v2``
     - ``POST``
     - Produce IIDM commands for the current step using EventStore.
   * - ``/user/control``
     - ``PUT``
     - Enqueue a single user control.
   * - ``/user/cluster_control``
     - ``PUT``
     - Validate and expand cluster controls.
   * - ``/user/controls``
     - ``GET``
     - Preview next-step controls.
   * - ``/user/status``
     - ``GET``
     - Return GameMaster service status (simulation + infrastructure health).
   * - ``/queue/list``
     - ``GET``
     - Inspect events with filters.
   * - ``/queue/{event_id}``
     - ``PUT``
     - Modify a pending DSL/trainer event (validate DSL, keep id/time_spec, enforce timing guards).
   * - ``/queue/summary``
     - ``GET``
     - Fetch per-status counts.
   * - ``/atomic/rt-user_control_dsl``
     - ``POST``
     - Apply DSL deltas to the upcoming simulation step (mounted under ``/atomic``).
   * - ``/logs/simulations``
     - ``GET``
     - List simulations that have DSL execution log entries, with first/last timestamps.
   * - ``/logs/sim/timeline/{simulation}``
     - ``GET``
     - Return the base DSL plus append/execution timeline for a simulation.
   * - ``/logs/sim/timeline/{simulation}/raw``
     - ``GET``
     - Reconstruct the DSL script (base + appends) as plain text for a simulation.

Core Classes
------------

+--------------------------------------------------------------+-------------------------------------------+
| Class                                                        | Responsibility                            |
+==============================================================+===========================================+
| ``SimulationController``                                     | Parses DSL, owns interpreter state,       |
| (``gamemaster.core.domain.controllers.scn_controller``)      | executes steps, and logs simulation meta. |
| ``UserControlManager``                                       | Validates user/cluster controls, persists |
| (``gamemaster.core.domain.controllers.user_controller``)     | them to EventStore, and exposes previews. |
| ``EventStore``                                               | SQLite-backed persistence for trainer,    |
| (``gamemaster.core.domain.event_store``)                     | user, and DSL events.                     |
| ``GameMasterNATSBridge``                                     | Keeps NATS subscriptions alive, publishes |
| (``gamemaster.core.services.nats.bridge``)                   | IIDM commands, and pushes status updates. |
| ``DependencySubscriptionManager``                            | Determines which measurement keys must    |
| (``gamemaster.core.services.dependency_subscription``)       | be subscribed based on DSL dependencies.  |
+--------------------------------------------------------------+-------------------------------------------+

Helper Functions
----------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Function
     - Description
   * - :func:`gamemaster.core.services.simulator_control_service.compute_simulator_control_commands`
     - Consumes the EventStore and returns v2 IIDM commands suitable for publication.
   * - :func:`gamemaster.core.utils.schema_loader.load_simulation_config_schema`
       / :func:`gamemaster.core.utils.schema_loader.load_iidm_command_schema_v2`
     - Load cached JSON schemas used by FastAPI routes and tests.
   * - :func:`gamemaster.core.utils.iidm_helper.extract_network_data`
       / :func:`gamemaster.core.utils.iidm_helper.serialize_network_data`
     - Convert IIDM files into cached JSON structures and back again.
   * - :func:`gamemaster.core.utils.clickhouse_client.get_clickhouse_client`
     - Returns the singleton ClickHouse-backed storage client with bucket-management helpers.
