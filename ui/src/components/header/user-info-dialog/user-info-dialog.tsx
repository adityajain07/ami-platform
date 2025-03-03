import { useUserInfo } from 'data-services/hooks/auth/useUserInfo'
import * as Dialog from 'design-system/components/dialog/dialog'
import { STRING, translate } from 'utils/language'
import { UserInfo } from 'utils/user/types'
import styles from './user-info-dialog.module.scss'
import { UserInfoForm } from './user-info-form/user-info-form'

export const UserInfoDialog = () => {
  const { userInfo } = useUserInfo()

  if (!userInfo) {
    return null
  }

  return (
    <>
      <Dialog.Root>
        <Dialog.Trigger>
          <div
            role="button"
            tabIndex={0}
            className={styles.userInfo}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                e.currentTarget.click()
              }
            }}
          >
            <UserInfoButtonContent userInfo={userInfo} />
          </div>
        </Dialog.Trigger>
        <Dialog.Content ariaCloselabel={translate(STRING.CLOSE)}>
          <Dialog.Header title="Edit user info" />
          <div className={styles.content}>
            <UserInfoForm userInfo={userInfo} />
          </div>
        </Dialog.Content>
      </Dialog.Root>
    </>
  )
}

const UserInfoButtonContent = ({ userInfo }: { userInfo: UserInfo }) => {
  const name = (() => {
    if (userInfo.name?.length) {
      return userInfo.name
    }
    if (userInfo.email?.length) {
      return userInfo.email
    }
    return '?'
  })()

  if (userInfo.image) {
    return <img alt={`Profile image for ${name}`} src={userInfo.image} />
  }

  return <span>{name.charAt(0)}</span>
}
