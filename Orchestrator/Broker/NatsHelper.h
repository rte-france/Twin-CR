/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef NATS_HELPER
#define NATS_HELPER

#include <functional>
#include <memory>
#include <string>

#include <nats.h>

using Handler = std::function<std::string(const natsMsg* msg)>;
inline std::vector<std::shared_ptr<Handler>> nats_handlers_;

/**
* @brief Static NATS message handler callback.
*
* This function is registered as a C-style callback with the NATS client library.
* It receives incoming messages on a subscribed subject, invokes a user-provided
* std::function (passed via the `closure` parameter), and publishes the result
* as a response.
*/
inline void NatsMessageHandlerWrapper(natsConnection* nc, natsSubscription* sub, natsMsg* msg, void* closure) {
    // Forward the call to the real instance method
    auto handler = static_cast<Handler*>(closure);
    std::string response = (*handler)(msg);

    // Send response
    const char* reply = natsMsg_GetReply(msg);
    if (reply != NULL) {
        natsConnection_PublishString(nc, reply, response.c_str());
    }
    (void) nc; (void) sub;
    natsMsg_Destroy(msg);
}

/**
* Replace . by _ in topic names because topics use . as separator.
* And also replace all reserved/forbidden characters (null space, *, >)
*/
inline void sanitizeNatsTopicName(std::string& topic) {
    for (char& c : topic) {
        switch (c) {
            case '\0': // null
            case ' ':  // space
            case '.':  // dot
            case '*':  // wildcard
            case '>':  // wildcard
                c = '_';
                break;
            default:
                // keep as is (includes all valid Unicode bytes)
                break;
        }
    }
}

/**
 * Subscribe to a topic on the nats server. The handler will then be called whenever a message
 * is published on this topic. The handler return string will be used to reply to the publisher
 * of the original message.
 * sub is taken by pointer-to-pointer (actually reference to pointer) as the pointer will be set in the natsConnection_Subscribe call
 */
inline void natsSubscribe(natsConnection* nc, natsSubscription*& sub, const std::string& topic, Handler handler) {
    auto handler_ptr = std::make_shared<Handler>(std::move(handler));
    nats_handlers_.push_back(handler_ptr);  // Keep reference to handler

    natsStatus s = natsConnection_Subscribe(&sub, nc, topic.c_str(), NatsMessageHandlerWrapper, handler_ptr.get());

    if (s != NATS_OK) {
        throw std::runtime_error("Subscription failed: " + std::string(natsStatus_GetText(s)));
    }
}

#endif // NATS_HELPER
