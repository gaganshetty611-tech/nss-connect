import { useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage } from '../services/api'

/** Run an async loader, tracking data/loading/error, re-running when deps change. */
export default function useAsync(loader, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  const mounted = useRef(true)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(loader, deps)

  const reload = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const data = await run()
      if (mounted.current) setState({ data, loading: false, error: null })
      return data
    } catch (e) {
      if (mounted.current) setState({ data: null, loading: false, error: errorMessage(e) })
      return null
    }
  }, [run])

  useEffect(() => {
    mounted.current = true
    reload()
    return () => {
      mounted.current = false
    }
  }, [reload])

  return { ...state, reload, setData: (data) => setState((s) => ({ ...s, data })) }
}
