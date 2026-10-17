/** Site-relative link that respects the Pages base path. url('teams/gen/') -> '/teams/gen/' (or '/<base>/teams/gen/' under a base path). */
export const url = (path = '') => `${import.meta.env.BASE_URL.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
