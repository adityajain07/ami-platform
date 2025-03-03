import { API_ROUTES, API_URL, STATUS_CODES } from 'data-services/constants'
import { UserInfo } from 'utils/user/types'
import { useUser } from 'utils/user/userContext'
import { useAuthorizedQuery } from './useAuthorizedQuery'

const REFETCH_INTERVAL = 10000 // Refetch every 10 second

export const useUserInfo = () => {
  const { user, clearToken } = useUser()
  const { data, isLoading, error } = useAuthorizedQuery<UserInfo>({
    queryKey: [API_ROUTES.ME],
    url: `${API_URL}/${API_ROUTES.ME}/`,
    refetchInterval: REFETCH_INTERVAL,
    retry: 0,
    onError: (error: any) => {
      if (error.response?.status === STATUS_CODES.FORBIDDEN) {
        if (user.loggedIn) {
          clearToken()
        }
      }
    },
  })

  return { userInfo: data, isLoading, error }
}
