package server

import (
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

// Berkas statis harus tersaji entah root ditulis dengan pemisah `/` atau `\`
// (Windows mengubah pemisah di dalam filepath.Clean).
func TestSajiStatisPemisahWindows(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "index.html"), []byte("<html></html>"), 0o644); err != nil {
		t.Fatal(err)
	}
	for _, varian := range []string{root, filepath.ToSlash(root), root + string(filepath.Separator)} {
		res := httptest.NewRecorder()
		if !sajiStatis(res, varian, "/") {
			t.Errorf("root %q: berkas index di '/' tidak tersaji", varian)
			continue
		}
		if res.Body.String() != "<html></html>" {
			t.Errorf("root %q: isi = %q", varian, res.Body.String())
		}
	}
}
