//go:build windows

package llama

import (
	"os/exec"
	"syscall"
)

// sembunyikanJendela mencegah jendela konsol ikut muncul saat llama-server
// dijalankan dari aplikasi desktop (padanan `windowsHide: true` di Node).
func sembunyikanJendela(cmd *exec.Cmd) {
	if cmd.SysProcAttr == nil {
		cmd.SysProcAttr = &syscall.SysProcAttr{}
	}
	cmd.SysProcAttr.HideWindow = true
}
