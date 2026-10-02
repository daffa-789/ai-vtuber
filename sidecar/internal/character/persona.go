package character

import (
	"fmt"
	"os"
)

// BacaPersona membaca berkas persona karakter.
func BacaPersona(path string) (string, error) {
	isi, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return "", fmt.Errorf("persona tidak ditemukan: %s", path)
		}
		return "", err
	}
	return string(isi), nil
}
