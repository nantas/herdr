# Agent-launched Herdr servers may pass NO_COLOR to interactive panes.
case $- in
    *i*) if [ "${HERDR_ENV:-}" = 1 ]; then unset NO_COLOR; fi ;;
esac
