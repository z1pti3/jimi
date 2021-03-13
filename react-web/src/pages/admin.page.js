import React, { Component, PureComponent } from "react";
import { useHistory } from 'react-router-dom';

import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

import configData from "./../config/config.json";
import { URL } from"./../utils/api";

import ClusterList from "./../components/clusterList.component"
import ClusterJobList from "./../components/clusterJobList.component"
import Loading from "./../components/loading.component"

import "../components/html.component.css"

import "./admin.page.css"

function apiClusterMembersRefresh() {
    const requestOptions = {
        method: 'GET',
        credentials: 'include',
    };
    var triggers = fetch(URL()+'cluster/', requestOptions).then(response => {
        if (response.ok) {
            return response.json()
        }
    }).then(json => {
        return json["results"];
    });
    return triggers
}

function apiJobsRefresh() {
    const requestOptions = {
        method: 'GET',
        credentials: 'include',
    };
    var triggers = fetch(URL()+'workers/stats/', requestOptions).then(response => {
        if (response.ok) {
            return response.json()
        } else {
            return []
        }
    }).then(json => {
        return json["results"];
    });
    return triggers
}

export default class AdminPage extends Component {
    constructor(props) {
        super(props);
        this.state = {
            clusterMembers : [],
            jobs : [],
            stats: [],
            loading: true
        }

        this.mounted = true;

        this.updateclusterMembers = this.updateClusterMembers.bind(this);
        apiClusterMembersRefresh().then(clusterMembers => {
            this.setState({ clusterMembers : clusterMembers, loading: false });
            this.updateClusterMembers();
        })

        this.updateJobs = this.updateJobs.bind(this);
        apiJobsRefresh().then(servers => {
            this.setState({ stats : servers });
            this.updateJobs();
        })

        this.clearCache = this.clearCache.bind(this);
        this.clearStartChecks = this.clearStartChecks.bind(this);
        this.deleteDebugSessions = this.deleteDebugSessions.bind(this);
        this.redistributeCluster = this.redistributeCluster.bind(this);
        this.deleteUnusedObjects = this.deleteUnusedObjects.bind(this);
    }

    componentWillUnmount() {
        this.mounted = false;
    }

    updateJobs() {
        if (this.mounted) {
            setTimeout(() => {
                apiJobsRefresh().then(servers => {
                    this.setState({ stats : servers });
                    this.updateJobs();
                })
            }, 2500 );
        }
    }

    updateClusterMembers() {
        if (this.mounted) {
            setTimeout(() => {
                apiClusterMembersRefresh().then(clusterMembers => {
                    this.setState({ clusterMembers : clusterMembers });
                    this.updateClusterMembers();
                })
            }, 15000 );
        }
    }

    clearCache() {
        const requestOptions = {
            method: 'GET',
            credentials: 'include',
        };
        var triggers = fetch(URL()+'clearCache/', requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            alert(JSON.stringify(json["results"]));
        });
    }

    clearStartChecks() {
        const requestOptions = {
            method: 'GET',
            credentials: 'include',
        };
        var triggers = fetch(URL()+'clearStartChecks/', requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            alert(JSON.stringify(json));
        });
    }

    deleteDebugSessions() {
        const requestOptions = {
            method: 'GET',
            credentials: 'include',
        };
        var triggers = fetch(URL()+'debug/clear/', requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            alert(JSON.stringify(json));
        });
    }

    redistributeCluster() {
        const requestOptions = {
            method: 'GET',
            credentials: 'include',
        };
        var triggers = fetch(URL()+'cluster/distribute/', requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            alert(JSON.stringify(json));
        });
    }

    deleteUnusedObjects() {
        this.props.history.push('/cleanup/'); 
    }

    render() {
        return !this.state.loading ? (
            <div className="pageContent1">
                <h1>Controls</h1>
                <hr/>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.clearCache}>Clear Cache</button>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.clearStartChecks}>Clear StartChecks</button>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.deleteDebugSessions}>Delete Debug Sessions</button>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.redistributeCluster}>Redistribute Cluster</button>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.deleteUnusedObjects}>Delete Unused Objects</button>
                <br/>
                <br/>
                <h1>Cluster Status</h1>
                <hr/>
                <ClusterList clusterMembers={this.state.clusterMembers} />
                <br/>
                <ResponsiveContainer width="100%" height={400}>
                    <BarChart data={this.state.stats} margin={{
                        top: 5,
                        right: 30,
                        left: 20,
                        bottom: 5
                    }}>
                        <XAxis dataKey="url" />
                        <YAxis />
                        <Legend />
                        <Bar dataKey="activeCount" fill="#82ca9d" />
                        <Bar dataKey="queueLength" fill="#8884d8" />
                    </BarChart>
                </ResponsiveContainer>
                {/* <ClusterJobList jobs={this.state.jobs} /> */}
            </div>
        ) : <Loading />
    }
}
