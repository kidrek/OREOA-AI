rule kit_test_marker {
    strings:
        $marker = "KIT-DFIR-TEST-MARKER"
    condition:
        $marker
}
