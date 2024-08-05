import './App.css';
import 'bootstrap/dist/css/bootstrap.css';
import axios from 'axios';
import { useState } from 'react';

function App() {
  const [s3File, setS3File] = useState('');
  const [isUploading, setUploading] = useState(false);
  const [statusText, setStatusText] = useState('')


  const uploadS3 = () => {
    setStatusText('Getting token for upload file')
    setUploading(true)

    const client = window.google.accounts.oauth2.initTokenClient({
      client_id: '917317928460-478cnshb1mdkcbesnk2kl1ian37ju7lf.apps.googleusercontent.com',
      scope: 'https://www.googleapis.com/auth/youtube.upload',
      ux_mode: 'popup',
      callback: (tokenResponse) => {
        if (tokenResponse && tokenResponse.access_token) {
          setStatusText('Getting token successfull!')

          if (window.google.accounts.oauth2.hasGrantedAnyScope(tokenResponse,
            'https://www.googleapis.com/auth/youtube.upload')) {
            setStatusText('Has access, sending token to BE for upload video')

            axios.post(`https://ktxqd5k118.execute-api.ap-southeast-1.amazonaws.com/api/upload-file`, { token: tokenResponse.access_token, file: s3File }, {
              headers: {
                'Content-Type': 'application/json',
              }
            })
              .then(res => {
                setStatusText('Upload done!' + JSON.stringify(res.statusText));
                console.log(res)
              })
              .catch(er => {
                setStatusText('Upload failed!' + JSON.stringify(er));
                console.log(er)
              }).finally(() => {
                setUploading(false)
              })

          }
        }
      },
      error_callback: (err) => {
        console.log(err);
        setStatusText('Get token failed');
        setUploading(false)
      }
    });
    
    client.requestAccessToken();
    
  }

  return (
    <div className="App">
      <h2>Demo</h2>
      <div className="panel panel-default">
        <div className="panel-heading">
          <p>Specific s3 file to be upload into youtube</p>
        </div>
        <div className="panel-body">
            <input type="text" name="file" value={s3File} onChange={(e) => setS3File(e.target.value)}/><br /><br />
            <input type="submit" value="Submit" id="submitBtn" onClick={uploadS3}/>
            <div id="submitSpinner" style={{visibility: isUploading ? "visible" : "hidden"}}>
              <div className="spinner-border"></div>
            </div>
            <p>{statusText}</p>
        </div>
      </div>
    </div>
  );
}

export default App;
