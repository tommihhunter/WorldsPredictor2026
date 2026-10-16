/** Site-relative link that respects the Pages base path. url('teams/gen/') -> '/poroprophet/teams/gen/'. */
export const url = (path = '') => `${import.meta.env.BASE_URL.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
