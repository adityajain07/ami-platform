import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import classNames from 'classnames'
import { Header } from 'components/header/header'
import { Menu } from 'components/menu/menu'
import { useProjectDetails } from 'data-services/hooks/projects/useProjectDetails'
import { Deployments } from 'pages/deployments/deployments'
import { Jobs } from 'pages/jobs/jobs'
import { Login } from 'pages/login/login'
import { Occurrences } from 'pages/occurrences/occurrences'
import { Overview } from 'pages/overview/overview'
import { Projects } from 'pages/projects/projects'
import { SessionDetails } from 'pages/session-details/session-details'
import { Sessions } from 'pages/sessions/sessions'
import { Species } from 'pages/species/species'
import { UnderConstruction } from 'pages/under-construction/under-construction'
import { useContext, useEffect } from 'react'
import { Navigate, Outlet, Route, Routes, useParams } from 'react-router-dom'
import {
  BreadcrumbContext,
  BreadcrumbContextProvider,
} from 'utils/breadcrumbContext'
import { getRoute } from 'utils/getRoute'
import { UserContextProvider } from 'utils/user/userContext'
import styles from './app.module.scss'

const queryClient = new QueryClient()

export const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <UserContextProvider>
        <BreadcrumbContextProvider>
          <ReactQueryDevtools initialIsOpen={false} />
          <div className={styles.wrapper}>
            <Header />
            <Routes>
              <Route
                path="/"
                element={
                  <Navigate
                    to={{
                      pathname: 'projects',
                      search: location.search,
                    }}
                    replace={true}
                  />
                }
              />
              <Route path="login" element={<LoginContainer />} />
              <Route path="projects" element={<ProjectsContainer />} />
              <Route path="projects/:projectId" element={<ProjectContainer />}>
                <Route path="" element={<Overview />} />
                <Route path="jobs/:id?" element={<Jobs />} />
                <Route path="deployments/:id?" element={<Deployments />} />
                <Route path="sessions" element={<Sessions />} />
                <Route path="sessions/:id" element={<SessionDetails />} />
                <Route path="occurrences/:id?" element={<Occurrences />} />
                <Route path="species/:id?" element={<Species />} />
                <Route path="*" element={<UnderConstruction />} />
              </Route>
            </Routes>
          </div>
        </BreadcrumbContextProvider>
      </UserContextProvider>
    </QueryClientProvider>
  )
}

const LoginContainer = () => (
  <main className={classNames(styles.main, styles.fullscreen)}>
    <Login />
  </main>
)

const ProjectsContainer = () => (
  <main className={styles.main}>
    <div className={styles.content}>
      <Projects />
    </div>
  </main>
)

const ProjectContainer = () => {
  const { projectId } = useParams()
  const projectDetails = useProjectDetails(projectId as string)
  const { setProjectBreadcrumb } = useContext(BreadcrumbContext)

  useEffect(() => {
    setProjectBreadcrumb({
      title: projectDetails.project?.name ?? '',
      path: getRoute({ projectId: projectId as string }),
    })

    return () => {
      setProjectBreadcrumb(undefined)
    }
  }, [projectDetails.project])

  return (
    <>
      <Menu />
      <main className={styles.main}>
        <div className={styles.content}>
          <Outlet context={projectDetails} />
        </div>
      </main>
    </>
  )
}
