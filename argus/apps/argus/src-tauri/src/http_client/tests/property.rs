/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use crate::http_client::utils::http_client::actor::url::build_api_url;
use proptest::prelude::*;

proptest! {
    #[test]
    fn prop_build_api_url_preserves_absolute(
        base in "[a-z]{3,6}://[a-z0-9.-]{1,20}",
        endpoint in "(http|https)://[a-z0-9.-]{1,20}(/[a-z0-9_]{1,10})*",
    ) {
        let res = build_api_url(&base, &endpoint);
        prop_assert_eq!(res, endpoint);
    }

    #[test]
    fn prop_build_api_url_no_duplicate_slashes_at_join(
        base in "https://[a-z0-9.-]{1,20}(/)?",
        path in "(/)?[a-z0-9_]{1,10}(/[a-z0-9_]{1,10})*",
    ) {
        let res = build_api_url(&base, &path);
        let base_trimmed = base.trim_end_matches('/');
        let path_trimmed = path.trim_start_matches('/');
        let expected = format!("{}/{}", base_trimmed, path_trimmed);
        prop_assert_eq!(&res, &expected);
        let after_protocol = &res[8..];
        prop_assert!(!after_protocol.contains("//"));
    }
}
