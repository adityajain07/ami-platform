import { QueryKey, useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { getAuthHeader } from 'data-services/utils'
import { useUser } from 'utils/user/userContext'

export const useAuthorizedQuery = <T>({
  onError,
  queryKey,
  refetchInterval,
  url,
}: {
  onError?: (error: unknown) => void
  queryKey: QueryKey
  refetchInterval?: number
  url: string
}) => {
  const { user } = useUser()

  const { data, isLoading, isFetching, error } = useQuery({
    refetchInterval,
    queryKey,
    queryFn: () =>
      axios
        .get<T>(url, {
          headers: getAuthHeader(user),
        })
        .then((res) => res.data),
    onError,
  })

  return { data, isLoading, isFetching, error }
}
