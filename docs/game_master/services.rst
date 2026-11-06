Services & Background Workers
=============================

GameMaster relies on several background processes to keep the simulator and
orchestrator ecosystems in sync. These services manage NATS connectivity,
dependency-driven measurement subscriptions, and simulator control command
generation.

Simulator Control Service
-------------------------

.. automodule:: gamemaster.core.services.simulator_control_service
   :members:
   :undoc-members:
   :show-inheritance:

Service Lifecycle Wiring
------------------------

.. automodule:: gamemaster.core.services
   :members:
   :undoc-members:

Dependency Subscription Manager
-------------------------------

.. automodule:: gamemaster.core.services.dependency_subscription
   :members:
   :undoc-members:

DSL Subscription Helper
-----------------------

.. automodule:: gamemaster.core.services.dsl_subscription
   :members:
   :undoc-members:

NATS Bridge
-----------

.. automodule:: gamemaster.core.services.nats.bridge
   :members:
   :undoc-members:
   :show-inheritance:

NATS Health Helpers
-------------------

.. automodule:: gamemaster.core.services.nats.health
   :members:
   :undoc-members:

Status Service
--------------

.. automodule:: gamemaster.core.services.status_service
   :members:
   :undoc-members:

Value Cache
-----------

.. automodule:: gamemaster.core.services.value_cache
   :members:
   :undoc-members:
