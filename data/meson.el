;; command to comment/uncomment text
(defun meson-comment-dwim (arg)
  "Comment or uncomment current line or region in a smart way.
For detail, see `comment-dwim'."
  (interactive "*P")
  (require 'newcomment)
  (let (
        (comment-start "#") (comment-end "")
        )
    (comment-dwim arg)))

;;(setq mymeson-keywords-regex (regex-opt '("if", "endif", "foreach", "endforeach")))

;; keywords for syntax coloring
(setq meson-keywords
      `(
        ( ,(regexp-opt '("if" "endif" "for" "foreach") 'word) . font-lock-keyword-face)
        )
      )

;; syntax table
(defvar meson-syntax-table nil "Syntax table for `meson-mode'.")
(setq meson-syntax-table
      (let ((synTable (make-syntax-table)))

        ;; bash style comment: “# …” 
        (modify-syntax-entry ?# "< b" synTable)
        (modify-syntax-entry ?\n "> b" synTable)

        synTable))

;; define the major mode.
(define-derived-mode meson-mode fundamental-mode
  "meson-mode is a major mode for editing Meson build definition files."
  :syntax-table meson-syntax-table
  
  (setq font-lock-defaults '(meson-keywords))
  (setq mode-name "meson")

  ;; modify the keymap
  (define-key meson-mode-map [remap comment-dwim] 'meson-comment-dwim)
)

