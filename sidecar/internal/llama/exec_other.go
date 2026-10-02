//go:build !windows

package llama

import "os/exec"

// sembunyikanJendela tidak melakukan apa pun di luar Windows.
func sembunyikanJendela(_ *exec.Cmd) {}
