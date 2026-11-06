/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef EVENT_QUEUE_H
#define EVENT_QUEUE_H

#include <atomic>
#include <cmath>
#include <functional>
#include <mutex>
#include <queue>

struct Callback {
    void* context;
    void (*func)(void*);

    void operator()() const { func(context); }
};

// Make callback from bound function
template<auto Method, typename T>
Callback makeCallback(T* instance) {
    return Callback {
        instance,
        [](void* ctx) {
            (static_cast<T*>(ctx)->*Method)();
        }
    };
}

// Make callback from static or free functions
template<auto Method>
Callback makeCallback() {
    return Callback{
        nullptr,
        [](void*) { Method(); }
    };
}

// Make callback from bound function with captures
template <auto Method, typename T, typename... Captures>
Callback makeCallback(T* instance, Captures&&... captures) {
    struct Context {
        T* instance;
        std::tuple<std::decay_t<Captures>...> captured;  // Decay forces capture by value (ensures ownership)

        Context(T* i, Captures&&... args)
            : instance(i), captured(std::forward<Captures>(args)...) {}

        static void call(void* ptr) {
            auto* ctx = static_cast<Context*>(ptr);
            std::apply([ctx](auto&&... args) {
                (ctx->instance->*Method)(std::forward<decltype(args)>(args)...);
            }, ctx->captured);
            delete ctx;  // Self-owning. Note that callbacks are thus only deleted when executed. Currently, creating a callback and cancelling it (deleting without calling it) would leak memory.
        }
    };

    return Callback{
        new Context(instance, std::forward<Captures>(captures)...),
        &Context::call
    };
}

class Event {
    public:
        /**
         * Where an event sits among the others scheduled for the very same time, lowest rank first.
         * Simultaneous events otherwise run in creation order.
         */
        enum class Order {
            Normal = 0,
            Dump = 1,         // The state dump has to see everything that happened at its own timestamp, otherwise it
                              // is saved under a time it does not describe, and a run resumed from it repeats that work
            DynawoStep = 2,   // Ensure all controls are registered before calling Dynawo (else, actions schedules for t=2s occur at t=3s if period=1s)
            CycosimStep = 3,  // Cycosim needs the Dynawo published values.
                              // Cycosim typically uses a smaller time steps, so controls from Cycosim will generally not be delayed by this order
        };

        Event(double time_, Callback&& callback_, Order order_ = Order::Normal) :
        time(time_),
        order(order_),
        callback(std::move(callback_)),
        id(count) {
            count++;  // Increment global count each time an event is created
        }

        // Mark event as move-only as copying functionals is expensive
        Event(Event&&) = default;
        Event& operator=(Event&&) = default;
        Event(const Event&) = delete;
        Event& operator=(const Event&) = delete;

        double time;
        Order order;
        Callback callback;
        void doEvent() { callback(); }

    private:
        static std::atomic<long> count;
        long id;

    friend bool operator<(Event const& lhs, Event const& rhs) {
        // Events with smaller time has higher priority
        if (lhs.time != rhs.time)
            return lhs.time > rhs.time;

        // Then by rank, so e.g. an Order::Dump event runs after the Order::Normal ones scheduled for that same time
        if (lhs.order != rhs.order)
            return lhs.order > rhs.order;

        // In case events occur at the same time, sort them by order of creation (guarantee stable sort)
        return lhs.id > rhs.id;
    }
};

inline std::atomic<long> Event::count = 0;

class EventQueue {
    public:
        virtual ~EventQueue() = default;
        /**
         * Insert event in the queue, keeping events ordered by event.time
         */
        virtual void insertEvent(Event&& event) = 0;
        virtual Event popNext() = 0;
        virtual bool isEmpty() = 0;
        virtual double nextTimeStep() = 0;
    protected:
        std::mutex mutex_;
};

template <typename Comparator>
class GenericEventQueue: public EventQueue {
    public:
        /**
         * Insert event in the queue, keeping events ordered
         */
        void insertEvent(Event&& event) {
            std::lock_guard<std::mutex> lock(mutex_);
            priority_queue_.push(std::move(event));
        }

        Event popNext() {
            std::lock_guard<std::mutex> lock(mutex_);
            // Black-magic trick to move an element out (instead of copy) from priority_queue_ (https://stackoverflow.com/a/20149745)
            // No other modifications than top/pop should be made around the const_cast
            auto next = std::move(const_cast<Event&>(priority_queue_.top()));
            priority_queue_.pop();
            return next;
        }

        bool isEmpty() {
            std::lock_guard<std::mutex> lock(mutex_);
            return priority_queue_.empty();
        }

        double nextTimeStep() {
            std::lock_guard<std::mutex> lock(mutex_);
            return priority_queue_.top().time;
        }
    private:
        std::priority_queue<Event, std::vector<Event>, Comparator> priority_queue_;
};

/**
 * Queue of events sorted in increasing order of event.time.
 * Events at the same time run by increasing Event::Order, and in creation order within one Order.
 * Note that the NonStrictEventQueue below honours neither, as it buckets times and ignores both fields.
 * In case of performance issues, the NonStrictQueue should be used instead (sorts events with less granularity).
 */
using StrictEventQueue = GenericEventQueue<std::less<Event>>;

const double NON_STRICT_QUEUE_ACCURACY = 0.1;  // 100ms accuracy

struct NonStrictEventComparator {
    bool operator()(const Event& lhs, const Event& rhs) const {
        int lhs_index = int(std::ceil(lhs.time / NON_STRICT_QUEUE_ACCURACY));
        int rhs_index = int(std::ceil(rhs.time / NON_STRICT_QUEUE_ACCURACY));
        return lhs_index > rhs_index; // earlier events = higher priority
    }
};

/**
 * Queue of events sorted in increasing order of event.time.
 * This particular queue sacrifices accuracy for performance, and puts events
 * on a discrete timeline with 100ms accuracy. There is no guarantee on the order of
 * Events that occur within 100ms of each others.
 */
using NonStrictEventQueue = GenericEventQueue<NonStrictEventComparator>;

#endif // EVENT_QUEUE_H
