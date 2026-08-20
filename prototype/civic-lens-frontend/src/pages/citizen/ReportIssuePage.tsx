import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { analyzeImageComplaint, checkDuplicates, transcribeAudio, extractLocationClues } from '../../api/ai';
import { calculatePriority, submitCitizenReport, getPublicIssueView } from '../../api/issues';
import { formatApiError } from '../../api/client';
import { CivicMap } from '../../components/maps/CivicMap';
import type { ComplaintAnalysis, DuplicateCheckResponse, PriorityAssessmentResult, RoutingDecisionResult, CandidateLocation } from '../../types';
import {
  FileText,
  Mic,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  Loader2,
  ShieldAlert,
  Clock,
  Building,
  Radio,
  Upload,
  MapPin
} from 'lucide-react';

export const ReportIssuePage: React.FC = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState<number>(1);
  const [inputType, setInputType] = useState<'text' | 'voice' | 'image'>('text');

  // Input states
  const [textInput, setTextInput] = useState<string>('');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [recordingTime, setRecordingTime] = useState<number>(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<any>(null);

  // Location state (Null by default, resolved by geocoder/GPS/map pin)
  const [selectedLocation, setSelectedLocation] = useState<[number, number] | null>(null);

  // Loading & Error states
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Location assistance state
  const [isExtractingLocation, setIsExtractingLocation] = useState<boolean>(false);
  const [candidateLocations, setCandidateLocations] = useState<CandidateLocation[]>([]);
  const [extractedTranscript, setExtractedTranscript] = useState<string | null>(null);
  const [extractedClues, setExtractedClues] = useState<any>(null);

  // Analysis & Engine results
  const [analysisResult, setAnalysisResult] = useState<ComplaintAnalysis | null>(null);
  const [duplicateResult, setDuplicateResult] = useState<DuplicateCheckResponse | null>(null);
  const [priorityResult, setPriorityResult] = useState<PriorityAssessmentResult | null>(null);
  const [routingResult, setRoutingResult] = useState<RoutingDecisionResult | null>(null);
  const [trackingId, setTrackingId] = useState<string>('');

  // Audio recording handlers
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        const file = new File([audioBlob], 'voice_complaint.wav', { type: 'audio/wav' });
        setAudioFile(file);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      setErrorMessage('Microphone access denied or not supported by browser.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      clearInterval(timerRef.current);
    }
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const maxBytes = 10 * 1024 * 1024; // 10 MB
      if (file.size > maxBytes) {
        setErrorMessage('Image is too large. Maximum allowed size is 10 MB.');
        setImageFile(null);
        setImagePreview(null);
        e.target.value = '';
        return;
      }
      setErrorMessage(null);
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      setErrorMessage('Geolocation is not supported by your browser.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setSelectedLocation([pos.coords.latitude, pos.coords.longitude]);
        setErrorMessage(null);
      },
      (err) => {
        setErrorMessage(`Unable to retrieve GPS location: ${err.message}`);
      }
    );
  };

  const handleExtractLocation = async () => {
    setErrorMessage(null);
    setIsExtractingLocation(true);
    setCandidateLocations([]);
    setSelectedLocation(null);
    setStep(2);

    try {
      let textForExtraction = textInput;
      
      if (inputType === 'voice') {
        if (!audioFile) throw new Error('Please record an audio complaint first.');
        const res = await transcribeAudio(audioFile);
        textForExtraction = res.transcription.text;
        setExtractedTranscript(textForExtraction);
      } else if (inputType === 'image') {
        if (!imageFile) throw new Error('Please upload an image file.');
        if (!textInput.trim()) {
           // Skip extraction if no text provided with image
           setIsExtractingLocation(false);
           return;
        }
      } else {
        if (!textInput.trim()) throw new Error('Please describe the issue in text.');
      }

      const locationRes = await extractLocationClues(textForExtraction);
      if (locationRes.clues) {
        setExtractedClues(locationRes.clues);
      } else {
        setExtractedClues(null);
      }

      if (locationRes.candidates && locationRes.candidates.length > 0) {
        setCandidateLocations(locationRes.candidates);
        // Default to first real candidate returned by geocoder
        setSelectedLocation([locationRes.candidates[0].latitude, locationRes.candidates[0].longitude]);
      } else if (locationRes.clues && locationRes.clues.confidence >= 0.7) {
        setCandidateLocations([]);
        setSelectedLocation(null);
        setErrorMessage(null); // Fallback to manual pin
      } else {
        setCandidateLocations([]);
        setSelectedLocation(null);
        setErrorMessage("The location could not be confidently identified from your description.");
      }
    } catch (err: any) {
      setCandidateLocations([]);
      setSelectedLocation(null);
      setErrorMessage("The location could not be confidently identified.");
    } finally {
      setIsExtractingLocation(false);
    }
  };

  // Process AI Analysis
  const handleAIAnalysis = async () => {
    if (!selectedLocation) {
      setErrorMessage("Please confirm a valid location on the map before proceeding.");
      return;
    }

    setErrorMessage(null);
    setIsAnalyzing(true);

    try {
      let analysis: ComplaintAnalysis;

      if (!imageFile) {
        throw new Error('A photo of the issue is strictly required.');
      }
      
      let descriptionText = textInput;
      if (inputType === 'voice') {
        if (!audioFile) {
          throw new Error('Please record an audio description.');
        }
        descriptionText = extractedTranscript || textInput;
      } else {
        if (!textInput.trim()) {
          throw new Error('Please describe the issue in text.');
        }
      }

      const res = await analyzeImageComplaint(imageFile, descriptionText);
      analysis = res.analysis;

      setAnalysisResult(analysis);

      // Duplicate Check against confirmed coordinates
      const dupRes = await checkDuplicates({
        text: analysis.summary || analysis.original_text,
        category: analysis.category,
        subcategory: analysis.subcategory,
        latitude: selectedLocation[0],
        longitude: selectedLocation[1],
        severity: analysis.severity,
        safety_risk: analysis.safety_risk,
        description: (analysis as any).detailed_description || analysis.original_text,
      });
      setDuplicateResult(dupRes);

      // Calculate Priority against confirmed coordinates
      const prioRes = await calculatePriority({
        category: analysis.category,
        subcategory: analysis.subcategory,
        severity: analysis.severity,
        safety_risk: analysis.safety_risk,
        public_impact: analysis.public_impact,
        location_description: analysis.location_description,
        latitude: selectedLocation[0],
        longitude: selectedLocation[1],
      });
      setPriorityResult(prioRes);

      // Submit the citizen report with strict photo enforcement and evidence association
      const formData = new FormData();
      formData.append('category', analysis.category);
      formData.append('subcategory', analysis.subcategory);
      formData.append('priority_score', prioRes.priority_score.toString());
      formData.append('priority_level', prioRes.priority_level);
      formData.append('latitude', selectedLocation[0].toString());
      formData.append('longitude', selectedLocation[1].toString());
      if (dupRes.matched_master_issue_id) {
         formData.append('issue_id', dupRes.matched_master_issue_id);
      }
      formData.append('photo', imageFile);
      if (inputType === 'voice' && audioFile) {
         formData.append('audio', audioFile);
      }
      
      const routeRes = await submitCitizenReport(formData);
      setRoutingResult(routeRes);

      // Resolve official public tracking ID
      try {
        const pubView = await getPublicIssueView(routeRes.issue_id);
        setTrackingId(pubView.public_id || routeRes.issue_id);
      } catch {
        setTrackingId(routeRes.issue_id);
      }

      setStep(3); // Advance to AI Understanding Verification
    } catch (err: any) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      {/* Step Indicator Header */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Report a Civic Issue</h1>
          <span className="text-xs text-blue-400 font-semibold px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full">
            Step {step} of 5
          </span>
        </div>

        <div className="grid grid-cols-5 gap-2">
          {[1, 2, 3, 4, 5].map((s) => (
            <div
              key={s}
              className={`h-2 rounded-full transition-all ${
                s <= step ? 'bg-blue-600' : 'bg-slate-200'
              }`}
            />
          ))}
        </div>
      </div>

      {errorMessage && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm flex items-center gap-3">
          <ShieldAlert className="w-5 h-5 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* STEP 1: Describe the issue */}
      {step === 1 && (
        <div className="bg-white/80 border border-slate-200 rounded-xl p-6 space-y-6">
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-slate-900">1. Describe the Issue</h3>
            <p className="text-xs text-slate-600">A photo of the problem is strictly required.</p>
          </div>

          {/* Mandatory Image Upload */}
          <div className="space-y-4">
            <div className="bg-white border border-dashed border-slate-200 rounded-lg p-6 text-center space-y-3">
              <Upload className="w-8 h-8 text-amber-400 mx-auto" />
              <p className="text-xs font-bold text-slate-800">Photo of the problem <span className="text-red-400">*</span></p>
              <p className="text-[10px] text-slate-600">JPG, PNG or WebP • Maximum 10 MB</p>
              <input
                type="file"
                accept="image/*"
                onChange={handleImageChange}
                className="hidden"
                id="civic-image-upload"
              />
              <label
                htmlFor="civic-image-upload"
                className="px-4 py-2 rounded-xl bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 text-xs font-semibold cursor-pointer inline-block border border-amber-600/30 transition-all"
              >
                Browse Photo
              </label>
              {imageFile && <p className="text-xs text-emerald-400 font-medium">âœ“ Selected: {imageFile.name}</p>}
            </div>
            
            {imagePreview && (
              <div className="rounded-lg border border-slate-200 bg-white p-2 flex items-center justify-center">
                <img src={imagePreview} alt="Preview" className="w-full h-auto max-h-96 object-contain rounded-xl" />
              </div>
            )}
          </div>

          {/* Description Method Tabs */}
          <div className="pt-4 border-t border-slate-200/50">
            <p className="text-xs font-medium text-slate-700 mb-3">How would you like to describe the problem?</p>
            <div className="grid grid-cols-2 gap-3 p-1 bg-white/80 border border-slate-200 rounded-xl">
              <button
                onClick={() => setInputType('text')}
                className={`py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 ${
                  inputType === 'text'
                    ? 'bg-blue-600 text-slate-900 shadow-md'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-white'
                }`}
              >
                <FileText className="w-4 h-4" /> Write Description
              </button>
              <button
                onClick={() => setInputType('voice')}
                className={`py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 ${
                  inputType === 'voice'
                    ? 'bg-emerald-600 text-slate-900 shadow-md'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-white'
                }`}
              >
                <Mic className="w-4 h-4" /> Record Voice
              </button>
            </div>
          </div>

          {/* Text Input */}
          {inputType === 'text' && (
            <div className="space-y-2 animate-in fade-in slide-in-from-top-2 duration-300">
              <textarea
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Describe what happened... (Required)"
                rows={4}
                className="w-full bg-white border border-slate-200 rounded-lg p-4 text-slate-900 text-sm focus:outline-none focus:border-blue-500 placeholder-slate-600"
              />
            </div>
          )}

          {/* Voice Input */}
          {inputType === 'voice' && (
            <div className="bg-white border border-slate-200 rounded-lg p-6 text-center space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mx-auto flex items-center justify-center">
                <Mic className={`w-6 h-6 ${isRecording ? 'animate-pulse text-red-400' : ''}`} />
              </div>

              {isRecording ? (
                <div className="space-y-2">
                  <p className="text-xs text-red-400 font-bold uppercase tracking-wider flex items-center justify-center gap-2">
                    <Radio className="w-4 h-4 animate-ping" /> Recording...
                  </p>
                  <p className="text-xl font-mono text-slate-900 font-bold">{recordingTime}s</p>
                  <button
                    onClick={stopRecording}
                    className="px-6 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-slate-900 font-semibold text-xs transition-all shadow-lg shadow-red-500/20"
                  >
                    Stop Recording
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <button
                    onClick={startRecording}
                    className="px-6 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-slate-900 font-semibold text-xs transition-all shadow-lg shadow-sm inline-flex items-center gap-2"
                  >
                    <Mic className="w-4 h-4" /> Start Audio Recording
                  </button>
                  {audioFile && (
                    <p className="text-xs text-emerald-400 font-semibold block">
                      âœ“ Voice recording saved
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              onClick={handleExtractLocation}
              className="px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-slate-900 font-semibold text-xs flex items-center gap-2 transition-all shadow-lg shadow-sm"
            >
              Next: Select Location <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: Location Selection */}
      {step === 2 && (
        <div className="bg-white/80 border border-slate-200 rounded-xl p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                2. Confirm Issue Location
                {isExtractingLocation && <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />}
              </h3>
              <p className="text-xs text-slate-600">
                {isExtractingLocation 
                  ? 'AI is extracting location clues from your complaint...'
                  : candidateLocations.length > 0
                    ? 'Select a candidate location below or click on the map to place a pin.'
                    : 'Location couldn\'t be automatically determined. Drop a pin or use GPS below.'}
              </p>
            </div>
            <div className="text-xs text-blue-400 font-mono font-semibold">
              {selectedLocation
                ? `Lat: ${selectedLocation[0].toFixed(4)}, Lng: ${selectedLocation[1].toFixed(4)}`
                : 'No location selected'}
            </div>
          </div>
          
          {candidateLocations.length > 0 && !isExtractingLocation && (
            <div className="flex flex-col gap-2 mb-4">
              <span className="text-xs text-slate-600 font-medium">Candidate Geocoded Locations:</span>
              <div className="flex flex-wrap gap-2">
                {candidateLocations.map((loc, idx) => {
                  const isSelected = selectedLocation && selectedLocation[0] === loc.latitude && selectedLocation[1] === loc.longitude;
                  const isOutside = loc.is_in_jurisdiction === false;
                  return (
                    <button
                      key={idx}
                      onClick={() => setSelectedLocation([loc.latitude, loc.longitude])}
                      className={`px-3 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all text-left ${
                        isSelected
                          ? 'bg-blue-600 text-slate-900 border-blue-500 shadow-md'
                          : isOutside
                          ? 'bg-white/90 text-slate-600 border-slate-200 hover:bg-slate-50'
                          : 'bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-700'
                      } border`}
                    >
                      <MapPin className="w-3.5 h-3.5 flex-shrink-0" />
                      <span className="truncate max-w-xs">{loc.display_name}</span>
                      <span className="opacity-75 font-mono">({(loc.confidence * 100).toFixed(0)}%)</span>
                      {isOutside && (
                        <span className="bg-amber-500/20 text-amber-300 text-[10px] px-1.5 py-0.5 rounded font-mono border border-amber-500/30 flex-shrink-0">
                          Outside Service Area
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {candidateLocations.length === 0 && !isExtractingLocation && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 space-y-3">
              <p className="text-xs text-amber-300 font-semibold flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                {extractedClues && extractedClues.confidence >= 0.7 ? (
                  <span>
                    We identified {extractedClues.raw_query || 'the location'}, but couldn't automatically locate the exact point. Please place a pin on the map to confirm the location.
                  </span>
                ) : (
                  <span>The location could not be confidently identified from your text.</span>
                )}
              </p>
              <div className="flex flex-wrap items-center gap-3 pt-1">
                <button
                  onClick={() => setStep(1)}
                  className="px-3 py-1.5 rounded-xl bg-slate-50 hover:bg-slate-700 text-slate-800 text-xs font-semibold border border-slate-300 flex items-center gap-1.5"
                >
                  <ArrowLeft className="w-3.5 h-3.5" /> Try describing again
                </button>
                <button
                  onClick={handleUseCurrentLocation}
                  className="px-3 py-1.5 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 text-xs font-semibold border border-emerald-500/30 flex items-center gap-1.5"
                >
                  <MapPin className="w-3.5 h-3.5" /> Use current location (GPS)
                </button>
                <span className="text-[11px] text-slate-600 font-medium">Or click anywhere on the map below to drop a pin manually</span>
              </div>
            </div>
          )}

          <CivicMap
            center={selectedLocation || [20.2961, 85.8245]}
            selectedLocation={selectedLocation}
            onLocationSelect={(lat, lng) => setSelectedLocation([lat, lng])}
            interactivePinPicker={true}
            className="h-96 w-full rounded-lg overflow-hidden border border-slate-200 shadow-xl"
          />

          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => setStep(1)}
              className="px-4 py-2.5 rounded-xl bg-slate-50 text-slate-700 text-xs font-semibold hover:bg-slate-700 flex items-center gap-1.5"
            >
              <ArrowLeft className="w-4 h-4" /> Back
            </button>

            <button
              onClick={handleAIAnalysis}
              disabled={!selectedLocation || isAnalyzing || isExtractingLocation}
              className="px-6 py-3 rounded-xl bg-blue-700 hover:bg-blue-800 text-white font-semibold text-xs flex items-center gap-2 transition-all shadow-md disabled:opacity-50"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Processing AI Engine...
                </>
              ) : (
                <>
                  Confirm Location & Analyze <Sparkles className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: AI Understanding Verification */}
      {step === 3 && analysisResult && (
        <div className="bg-white/80 border border-slate-200 rounded-xl p-6 space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-blue-400" /> 3. AI Complaint Understanding
            </h3>
            <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full font-semibold">
              Confidence: {(analysisResult.confidence * 100).toFixed(0)}%
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white/80 border border-slate-200 rounded-lg p-4 space-y-2">
              <span className="text-xs text-slate-600 font-medium uppercase tracking-wider block">Detected Language</span>
              <p className="text-base font-bold text-slate-900 uppercase">{analysisResult.language || 'English (en)'}</p>
              <p className="text-[11px] text-slate-500">Detector: {analysisResult.language_detector}</p>
            </div>

            <div className="bg-white/80 border border-slate-200 rounded-lg p-4 space-y-2">
              <span className="text-xs text-slate-600 font-medium uppercase tracking-wider block">Category & Subcategory</span>
              <div className="flex items-center space-x-2">
                <span className="bg-blue-100 text-blue-400 border border-blue-200 text-xs px-2.5 py-1 rounded-lg font-bold">
                  {analysisResult.category}
                </span>
                <span className="text-slate-700 text-xs font-semibold">{analysisResult.subcategory}</span>
              </div>
            </div>

            <div className="bg-white/80 border border-slate-200 rounded-lg p-4 space-y-2">
              <span className="text-xs text-slate-600 font-medium uppercase tracking-wider block">Severity & Safety Risk</span>
              <div className="flex items-center space-x-3">
                <span className="text-lg font-bold text-slate-900">{analysisResult.severity} / 5</span>
                {analysisResult.safety_risk ? (
                  <span className="bg-red-500/10 text-red-400 border border-red-500/20 text-xs px-2.5 py-1 rounded-full font-bold flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" /> High Safety Risk
                  </span>
                ) : (
                  <span className="text-xs text-slate-600">Normal Municipal Issue</span>
                )}
              </div>
            </div>

            <div className="bg-white/80 border border-slate-200 rounded-lg p-4 space-y-2">
              <span className="text-xs text-slate-600 font-medium uppercase tracking-wider block">Generated English Summary</span>
              <p className="text-xs text-slate-800 leading-relaxed font-medium">{analysisResult.summary}</p>
            </div>
          </div>

          <div className="flex justify-between items-center pt-2">
            <button
              onClick={() => setStep(1)}
              className="px-4 py-2.5 rounded-xl bg-slate-50 text-slate-700 text-xs font-semibold hover:bg-slate-700"
            >
              Edit Details
            </button>
            <button
              onClick={() => setStep(4)}
              className="px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-slate-900 font-semibold text-xs flex items-center gap-2 shadow-lg shadow-sm"
            >
              Next: Check Duplicates <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: Duplicate Detection */}
      {step === 4 && duplicateResult && (
        <div className="bg-white/80 border border-slate-200 rounded-xl p-6 space-y-6">
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-slate-900">4. Duplicate Detection Engine</h3>
            <p className="text-xs text-slate-600">Checking vector similarity against nearby reported Master Issues</p>
          </div>

          {duplicateResult.action === 'AUTOMATIC_MERGE' && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-6 space-y-4">
              <div className="flex items-center space-x-3 text-amber-400">
                <AlertTriangle className="w-6 h-6 flex-shrink-0" />
                <div>
                  <h4 className="font-bold text-sm">This issue has already been reported in your area</h4>
                  <p className="text-xs text-slate-700">
                    Merged into Master Issue <span className="font-mono text-amber-300">{duplicateResult.matched_master_issue_id}</span>
                  </p>
                </div>
              </div>

              <div className="bg-white/60 rounded-xl p-4 text-xs space-y-2 border border-slate-200">
                <div className="flex justify-between text-slate-600">
                  <span>Anonymous Community Reports:</span>
                  <span className="text-slate-900 font-bold">{duplicateResult.citizen_reporter_count} Citizens</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Spatial Match Score:</span>
                  <span className="text-amber-400 font-bold">{(duplicateResult.total_score * 100).toFixed(0)}% Match</span>
                </div>
              </div>

              <p className="text-xs text-slate-600">
                Your report adds weight to this issue's priority without creating a duplicate ticket. Complainant identity remains anonymous.
              </p>
            </div>
          )}

          {duplicateResult.action === 'HUMAN_REVIEW_RECOMMENDED' && (
            <div className="bg-blue-500/10 border border-blue-200 rounded-lg p-6 space-y-4">
              <div className="flex items-center space-x-3 text-blue-400">
                <AlertTriangle className="w-6 h-6 flex-shrink-0" />
                <div>
                  <h4 className="font-bold text-sm">Possible Duplicate Detected</h4>
                  <p className="text-xs text-slate-700">
                    Flagged for human review against Master Issue <span className="font-mono text-blue-700">{duplicateResult.matched_master_issue_id}</span>
                  </p>
                </div>
              </div>

              <div className="bg-white/60 rounded-xl p-4 text-xs space-y-2 border border-slate-200">
                <div className="flex justify-between text-slate-600">
                  <span>Anonymous Community Reports:</span>
                  <span className="text-slate-900 font-bold">{duplicateResult.citizen_reporter_count} Citizens</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Spatial Match Score:</span>
                  <span className="text-blue-400 font-bold">{(duplicateResult.total_score * 100).toFixed(0)}% Match</span>
                </div>
              </div>

              <p className="text-xs text-slate-600">
                Your report has been recorded. A moderator will verify if it matches the existing issue. Complainant identity remains anonymous.
              </p>
            </div>
          )}

          {duplicateResult.action === 'NEW_MASTER_ISSUE' && (
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-6 space-y-3">
              <div className="flex items-center space-x-3 text-emerald-400">
                <CheckCircle2 className="w-6 h-6 flex-shrink-0" />
                <div>
                  <h4 className="font-bold text-sm">New Master Issue Verified</h4>
                  <p className="text-xs text-slate-700">No duplicate Master Issue found nearby. Registering new ticket <span className="font-mono text-emerald-300">{duplicateResult.matched_master_issue_id}</span>.</p>
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              onClick={() => setStep(5)}
              className="px-6 py-3 rounded-xl bg-blue-700 hover:bg-blue-800 text-white font-semibold text-xs flex items-center gap-2 shadow-md"
            >
              Confirm & Submit Report <CheckCircle2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 5: Submission Confirmation */}
      {step === 5 && (
        <div className="bg-white/90 border border-slate-200 rounded-xl p-8 text-center space-y-6">
          <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 mx-auto flex items-center justify-center">
            <CheckCircle2 className="w-10 h-10" />
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl font-extrabold text-slate-900">Complaint Submitted Successfully!</h2>
            <p className="text-xs text-slate-600">Your complaint has been routed to the appropriate municipal authority.</p>
          </div>

          {/* Tracking Card */}
          <div className="bg-white border border-slate-200 rounded-lg p-6 max-w-lg mx-auto text-left space-y-4 shadow-xl">
            <div className="flex justify-between items-center pb-3 border-b border-slate-200">
              <span className="text-xs text-slate-600 font-medium uppercase">CivicLens Tracking ID</span>
              <span className="font-mono text-sm font-bold text-blue-400">{trackingId}</span>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-slate-500 block">Assigned Department</span>
                <span className="font-bold text-slate-900 flex items-center gap-1 mt-0.5">
                  <Building className="w-3.5 h-3.5 text-blue-400" /> {routingResult?.primary_department || routingResult?.assigned_department || 'Routing Pending...'}
                </span>
              </div>

              <div>
                <span className="text-slate-500 block">Priority Tier</span>
                <span className="font-bold text-amber-400 flex items-center gap-1 mt-0.5">
                  <AlertTriangle className="w-3.5 h-3.5" /> {priorityResult?.priority_level || priorityResult?.priority_tier || 'HIGH'}
                </span>
              </div>

              <div>
                <span className="text-slate-500 block">Current Status</span>
                <span className="font-bold text-emerald-400 mt-0.5 block">ROUTED</span>
              </div>

              <div>
                <span className="text-slate-500 block">SLA Target Resolution</span>
                <span className="font-bold text-slate-900 flex items-center gap-1 mt-0.5">
                  <Clock className="w-3.5 h-3.5 text-purple-400" /> {routingResult?.sla?.resolution_minutes ? `${Math.round(routingResult.sla.resolution_minutes / 60)} Hours` : '24 Hours'}
                </span>
              </div>
            </div>
          </div>

          <div className="flex justify-center space-x-4 pt-4">
            <button
              onClick={() => navigate('/citizen/issues')}
              className="px-6 py-3 rounded-xl bg-blue-700 hover:bg-blue-800 text-white font-semibold text-xs transition-all shadow-md"
            >
              Track in My Issues
            </button>
            <button
              onClick={() => {
                setStep(1);
                setTextInput('');
                setImageFile(null);
                setAudioFile(null);
              }}
              className="px-6 py-3 rounded-xl bg-slate-50 text-slate-700 text-xs font-semibold hover:bg-slate-700"
            >
              Report Another Issue
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

